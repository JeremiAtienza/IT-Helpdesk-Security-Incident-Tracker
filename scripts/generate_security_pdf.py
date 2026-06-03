import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def load_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Could not read {path}: {e}"


def pretty_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return json.dumps(data, indent=2)
    except Exception as e:
        return load_file(path)


def build_pdf(out_path='security_audit_report.pdf'):
    doc = SimpleDocTemplate(out_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph('Security Audit Report', styles['Title']))
    story.append(Spacer(1, 12))

    story.append(Paragraph('pip-audit results', styles['Heading2']))
    story.append(Paragraph('<pre>%s</pre>' % pretty_json('pip_audit.json'), styles['Code']))
    story.append(Spacer(1, 12))

    story.append(Paragraph('Bandit results', styles['Heading2']))
    story.append(Paragraph('<pre>%s</pre>' % pretty_json('bandit.json'), styles['Code']))
    story.append(Spacer(1, 12))

    story.append(Paragraph('Django check --deploy', styles['Heading2']))
    story.append(Paragraph('<pre>%s</pre>' % load_file('django_check.txt'), styles['Code']))

    doc.build(story)


if __name__ == '__main__':
    build_pdf()
    print('security_audit_report.pdf created')
