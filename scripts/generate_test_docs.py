import pymupdf as fitz
from docx import Document
from pathlib import Path

def generate_docs():
    # Умный путь: ищем папку data/docs относительно расположения этого скрипта
    docs_dir = Path(__file__).parent.parent / "data" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Генерация документов в: {docs_dir.absolute()}")

    # 1. Генерация Markdown (.md)
    md_content = """# Политика информационной безопасности

## 1. Общие положения
Настоящая политика определяет правила обработки конфиденциальной информации в компании.
Все сотрудники обязаны строго соблюдать данные правила для защиты данных.

## 2. Правила работы с паролями
Пароль должен содержать не менее 12 символов, включая цифры и спецсимволы.
Категорически запрещается передавать пароли третьим лицам или записывать их на стикерах.
"""
    (docs_dir / "security_policy.md").write_text(md_content, encoding="utf-8")
    print("✅ Создан: security_policy.md")

    # 2. Генерация DOCX (.docx)
    doc = Document()
    doc.add_heading('Политика отпусков и рабочих часов', 0)
    
    doc.add_heading('1. Продолжительность рабочего дня', level=1)
    doc.add_paragraph('Стандартный рабочий день составляет 8 часов. Начало работы в 9:00, окончание в 18:00.')
    
    doc.add_heading('2. Оформление отпуска', level=1)
    doc.add_paragraph('Заявление на ежегодный оплачиваемый отпуск подается не менее чем за 2 недели до начала.')
    
    doc.save(docs_dir / "hr_policy.docx")
    print("✅ Создан: hr_policy.docx")

    # 3. Генерация PDF (.pdf)
    # Используем английский текст, так как стандартный шрифт PyMuPDF при создании 
    # PDF с нуля не поддерживает кириллицу (превращает её в точки).
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    
    # Заголовок (размер > 12, чтобы наш парсер его распознал)
    page.insert_text((50, 50), "Data Protection Guidelines", fontsize=16)
    
    # Обычный текст (размер <= 12)
    page.insert_text((50, 100), "All employees must follow these data protection guidelines.", fontsize=11)
    page.insert_text((50, 130), "Section 1: Do not share your password with anyone under any circumstances.", fontsize=11)
    
    pdf_doc.save(docs_dir / "data_protection.pdf")
    pdf_doc.close()
    print("✅ Создан: data_protection.pdf")

    print("\n🎉 Все тестовые документы успешно созданы!")

if __name__ == "__main__":
    generate_docs()