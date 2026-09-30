#!/usr/bin/env python3
"""Validate coverage, Q/A pairing and final PDF text; produce visual-review sheets."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf
from docx import Document
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study-preview', type=Path, required=True)
    parser.add_argument('--answer-preview', type=Path, required=True)
    parser.add_argument('--sheets', type=Path, default=Path('/tmp/visionlab-review-sheets'))
    args = parser.parse_args()
    content = json.loads((HERE / 'content.json').read_text())
    entries = content['entries']
    expected = [f'Q{e["number"]:03d}-{j}' for e in entries for j in range(1, 7)]
    assert len(entries) == 140 and len(expected) == 840
    assert len(content['architectures']) == 22
    results = {'algorithm_count': 140, 'questions_per_algorithm': 6,
               'question_count': 840, 'model_architecture_count': 22, 'books': {}}
    args.sheets.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    for label, stem, preview, answers in [
        ('study', '01_140算法原理与练习', args.study_preview, False),
        ('answers', '02_140算法练习参考答案', args.answer_preview, True),
    ]:
        path = OUT / f'{stem}.docx'
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs]
        actual = [m.group() for t in paragraphs if (m := re.match(r'Q\d{3}-[1-6]\b', t))]
        assert actual == expected, (label, 'missing or reordered questions')
        actual_answers = [t.removeprefix('参考答案：') for t in paragraphs if t.startswith('参考答案：')]
        expected_answers = [qa['answer'] for e in entries for qa in e['qa']] if answers else []
        assert actual_answers == expected_answers, (label, 'answer pairing')
        for e in entries:
            assert any(t.startswith(f'{e["number"]:03d}  {e["name"]}') for t in paragraphs), e['id']
        assert not any(token in '\n'.join(paragraphs) for token in ['TODO', 'TBD', '待补充', '�'])
        pdf = pymupdf.open(preview / f'{stem}.pdf')
        text = '\n'.join(page.get_text() for page in pdf)
        # The answer introduction explains Q001-1 once; paragraph-leading IDs are
        # used above for exact counting, while PDF checks verify no export loss.
        ids = Counter(re.findall(r'Q\d{3}-[1-6]\b', text))
        assert set(ids) == set(expected), (label, 'PDF export lost questions')
        sparse, overflow, blank = [], [], []
        for pno, page in enumerate(pdf, 1):
            body = [b for b in page.get_text('blocks') if 55 <= b[1] < 785 and b[6] == 0]
            chars = sum(len(b[4].strip()) for b in body)
            if chars < 180:
                sparse.append({'page': pno, 'body_characters': chars,
                               'excerpt': ' '.join(b[4] for b in body)[:160]})
            if not body:
                blank.append(pno)
            for b in body:
                if b[0] < 74 or b[2] > 535 or b[3] > 791:
                    overflow.append({'page': pno, 'bbox': list(b[:4]), 'excerpt': b[4][:120]})
        assert not blank, (label, 'blank pages', blank)
        assert not overflow, (label, 'text outside page area', overflow)
        images = sorted(preview.glob('page-*.png'))
        assert len(images) == len(pdf), (label, 'missing page previews')
        sheets = []
        for offset in range(0, len(images), 25):
            batch = images[offset:offset + 25]
            cell_w, cell_h = 235, 358
            sheet = Image.new('RGB', (cell_w * 5, cell_h * 5), '#b8bec5')
            draw = ImageDraw.Draw(sheet)
            for i, page_path in enumerate(batch):
                im = Image.open(page_path).convert('RGB')
                im.thumbnail((225, 320))
                x = i % 5 * cell_w + (cell_w - im.width) // 2
                y = i // 5 * cell_h + 29
                sheet.paste(im, (x, y))
                draw.text((i % 5 * cell_w + 8, i // 5 * cell_h + 5),
                          f'{label} {offset+i+1:03d}', fill='black', font=font)
            target = args.sheets / f'{label}-{offset+1:03d}-{offset+len(batch):03d}.jpg'
            sheet.save(target, quality=92)
            sheets.append(str(target))
        results['books'][label] = {
            'docx': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'pdf_pages': len(pdf), 'exact_docx_question_count': len(actual),
            'exact_answer_count': len(actual_answers), 'pdf_unique_question_count': len(ids),
            'blank_pages': blank, 'text_overflow': overflow, 'sparse_pages_for_review': sparse,
            'review_sheets': sheets,
        }
        print(label, 'pages:', len(pdf), 'questions:', len(actual), 'answers:', len(actual_answers))
        print('Sparse pages:', json.dumps(sparse, ensure_ascii=False))
    results['automated_checks_pass'] = True
    (OUT / 'quality' / 'validation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
