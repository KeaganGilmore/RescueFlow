import os
import sys
import json
import hashlib
import fitz  # PyMuPDF
import asyncio
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PDF_DIR = "pdfs"
DOCS_DIR = "docs"
IMAGES_DIR = os.path.join(DOCS_DIR, "images")
THUMBNAILS_DIR = os.path.join(IMAGES_DIR, "thumbnails")

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

# Semaphore to limit concurrent OpenAI calls
SEM = asyncio.Semaphore(5)

# Global set to track image hashes for deduplication (e.g. repeated headers/footers)
_seen_image_hashes = {}


def sanitize_filename(name):
    """Replace spaces and special chars with underscores for web-safe filenames."""
    return re.sub(r'[^\w\-.]', '_', name)


def extract_images_from_page(page, module_name, page_num):
    """Extract unique images from a PDF page, deduplicating by content hash."""
    image_list = page.get_images(full=True)
    saved_images = []
    safe_module = sanitize_filename(module_name)

    for img_index, img in enumerate(image_list):
        xref = img[0]
        try:
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # Skip very small images (likely icons/decorations < 2KB)
            if len(image_bytes) < 2048:
                continue

            # Deduplicate: hash the image bytes
            img_hash = hashlib.md5(image_bytes).hexdigest()

            if img_hash in _seen_image_hashes:
                # Already saved this exact image, reuse the path
                saved_images.append(_seen_image_hashes[img_hash])
                continue

            image_filename = f"{safe_module}_p{page_num + 1}_img{img_index + 1}.{image_ext}"
            image_path = os.path.join(IMAGES_DIR, image_filename)

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            relative_path = f"images/{image_filename}"
            _seen_image_hashes[img_hash] = relative_path
            saved_images.append(relative_path)
        except Exception as e:
            print(f"  Warning: Could not extract image {img_index} on page {page_num}: {e}")

    return saved_images


def extract_links_from_page(page, text):
    links = set()
    for link in page.get_links():
        if link.get("uri"):
            links.add(link["uri"])
    text_links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
    for tl in text_links:
        links.add(tl)
    return list(links)


async def process_page_with_gpt(text, images, links, page_num):
    link_context = ""
    if links:
        link_context = f"\nDetected links on this page: {json.dumps(links)}. If any are video links (YouTube, Vimeo), embed them using an HTML iframe (16:9 aspect ratio)."

    prompt = f"""
    You are an expert educational content structurer.
    
    Task:
    1. Analyze the following text (from Page {page_num + 1}) and extract a short, descriptive **Section Title** (e.g., "Safety Procedures" or "Introduction"). Do NOT use "Page {page_num+1}" as the title.
    2. Convert the extracted PDF text into clean, structured Markdown.
       - **IMPORTANT**: Return ONLY the markdown content. Do NOT wrap it in ```markdown code blocks.
    3. Keep all headers and logical structure.
    4. If the text describes a diagram or image, insert it using the EXACT path from this list: {json.dumps(images)}.
       Use markdown syntax: ![Description](exact_path_from_list)
       Do NOT modify the image path in any way.
    5. {link_context}
    6. At the very end of the response, generate a JSON object containing the Title, Quiz, and a brief 1-sentence Summary of this section.
       **IMPORTANT**: Only generate a quiz if this section contains genuine educational/instructional content (facts, procedures, concepts a learner should retain).
       Do NOT generate a quiz for: tables of contents, catalogues, indexes, organizational charts, contact info pages, title pages, or other reference-only material.
       If no quiz is appropriate, return an empty quiz array.
       The JSON must be strictly formatted as:
       ```json
       {{
         "title": "Descriptive Section Title",
         "summary": "Brief summary of this section.",
         "quiz": [
           {{
             "question": "Question text?",
             "options": ["A", "B", "C", "D"],
             "correct": 0
           }}
         ]
       }}
       ```
    
    Input Text:
    {text}
    """

    async with SEM:
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that converts PDF text to Markdown and generates quizzes. You output raw markdown followed by a JSON block. When inserting images, use the EXACT file paths provided to you without modification."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            content = response.choices[0].message.content
            return parse_gpt_response(content)
        except Exception as e:
            print(f"  Error calling OpenAI for page {page_num}: {e}")
            return text, "Page Error", []


def parse_gpt_response(response_text):
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)

    markdown_content = response_text
    metadata = {"title": "Untitled Section", "summary": "", "quiz": []}

    if json_match:
        json_str = json_match.group(1)
        try:
            extracted_data = json.loads(json_str)
            metadata.update(extracted_data)
            markdown_content = response_text.replace(json_match.group(0), "").strip()
            # Remove any wrapping ```markdown blocks
            markdown_content = re.sub(r"^```markdown\s*", "", markdown_content)
            markdown_content = re.sub(r"\s*```$", "", markdown_content)
        except json.JSONDecodeError:
            print("  Warning: Failed to decode JSON from GPT response")

    return markdown_content, metadata["title"], metadata["quiz"]


async def generate_course_thumbnail(module_id, course_title, chapter_titles):
    """Generate a course thumbnail using DALL-E 3. Cached by file existence."""
    thumb_path = os.path.join(THUMBNAILS_DIR, f"{module_id}.png")
    thumb_relative = f"images/thumbnails/{module_id}.png"

    if os.path.exists(thumb_path):
        print(f"  [CACHED] Thumbnail for {course_title}")
        return thumb_relative

    print(f"  Generating thumbnail for {course_title}...")

    topics = ", ".join(chapter_titles[:8])
    prompt_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                f"I need a DALL-E image generation prompt for a course thumbnail.\n"
                f"Course: {course_title}\n"
                f"Topics covered: {topics}\n\n"
                f"Write a single short DALL-E prompt (max 50 words) for a professional, "
                f"cinematic photograph or realistic 3D render that represents this course. "
                f"Style: dramatic lighting, realistic textures, professional stock-photo quality. "
                f"Think editorial photography or high-end corporate training material. "
                f"NO cartoon, NO flat illustration, NO clip-art, NO text in the image.\n"
                f"Reply with ONLY the prompt, nothing else."
            )
        }],
        max_tokens=100
    )
    dalle_prompt = prompt_response.choices[0].message.content.strip()
    print(f"    Prompt: {dalle_prompt[:80]}...")

    try:
        image_response = await client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = image_response.data[0].url

        async with httpx.AsyncClient() as http:
            img_data = await http.get(image_url)
            with open(thumb_path, "wb") as f:
                f.write(img_data.content)

        print(f"    Saved: {thumb_path}")
        return thumb_relative
    except Exception as e:
        print(f"    Failed to generate thumbnail: {e}")
        return ""


async def process_pdf(pdf_file):
    module_name = os.path.splitext(pdf_file)[0]
    print(f"\nProcessing: {module_name}")

    doc = fitz.open(os.path.join(PDF_DIR, pdf_file))

    module_id = sanitize_filename(module_name).lower()
    course_title = module_name.replace("_", " ").title()

    module_data = {
        "id": module_id,
        "title": course_title,
        "description": f"Training module derived from {pdf_file}",
        "thumbnail": "",
        "chapters": []
    }

    tasks = []

    for page_num, page in enumerate(doc):
        images = extract_images_from_page(page, module_name, page_num)
        text = page.get_text()
        links = extract_links_from_page(page, text)
        tasks.append(process_page_with_gpt(text, images, links, page_num))

    print(f"  Sending {len(tasks)} pages to GPT-4o...")
    results = await asyncio.gather(*tasks)

    for i, (markdown, title, quizzes) in enumerate(results):
        module_data["chapters"].append({
            "id": f"{module_id}_ch{i}",
            "title": title,
            "content": markdown,
            "quiz": quizzes
        })

    # Generate AI thumbnail
    chapter_titles = [ch["title"] for ch in module_data["chapters"]]
    module_data["thumbnail"] = await generate_course_thumbnail(module_id, course_title, chapter_titles)

    return module_id, module_data


async def main():
    print("=== RescueFlow Build ===")
    print(f"  PDFs dir:   {os.path.abspath(PDF_DIR)}")
    print(f"  Output dir: {os.path.abspath(DOCS_DIR)}")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR}/")
        return

    print(f"  Found {len(pdf_files)} PDF(s): {', '.join(pdf_files)}")

    # Clear the dedup cache for fresh build
    _seen_image_hashes.clear()

    course_data = {}
    for pdf_file in pdf_files:
        module_id, data = await process_pdf(pdf_file)
        course_data[module_id] = data

    # Write output
    output_path = os.path.join(DOCS_DIR, "course_data.js")
    js_content = f"window.COURSE_DATA = {json.dumps(course_data, indent=2)};"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    # Summary
    total_chapters = sum(len(m["chapters"]) for m in course_data.values())
    total_images = len(_seen_image_hashes)
    print(f"\n=== Build Complete ===")
    print(f"  Modules:  {len(course_data)}")
    print(f"  Chapters: {total_chapters}")
    print(f"  Unique images: {total_images}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
