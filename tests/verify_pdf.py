import logging
from pathlib import Path
from amanu.plugins.pdf import PDFPlugin

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_pdf_generation():
    plugin = PDFPlugin()
    
    # Dummy context with Cyrillic text
    context = {
        "summary": "Это тестовое резюме на русском языке.",
        "date": "2023-10-27",
        "participants": ["Иван Иванов", "Петр Петров"],
        "key_takeaways": ["Первый важный пункт", "Второй важный пункт"],
        "clean_text": "Это полный текст транскрипции. Он должен отображаться корректно, без квадратиков. Проверка шрифта DejaVuSans."
    }
    
    # Load one of the new templates
    template_path = Path("amanu/templates/pdf/modern.j2")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    output_path = Path("test_output.pdf")
    
    print(f"Generating PDF to {output_path}...")
    try:
        plugin.generate(context, template_content, output_path)
        print("PDF generation successful!")
        if output_path.exists():
            print(f"File created: {output_path} (Size: {output_path.stat().st_size} bytes)")
        else:
            print("Error: File not found after generation.")
    except Exception as e:
        print(f"PDF generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_generation()
