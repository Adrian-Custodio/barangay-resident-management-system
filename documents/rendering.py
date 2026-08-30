"""
Fills a DocumentType's template_body in with a specific resident's data.

template_body's own help_text documents it as containing real Django
template syntax ("{{resident.full_name}}"), so this reuses Django's
Template engine directly rather than inventing a bespoke placeholder
mini-language -- it already does variable substitution and safe HTML
escaping, which is exactly what's needed. Rendering arbitrary template
strings is normally a code-injection concern, but template_body is only
ever edited by ADMIN users (see accounts.mixins.AdminRequiredMixin on the
DocumentType views), and Django templates can't execute arbitrary Python
regardless -- only reach attributes/methods already exposed to the
context.
"""
from django.template import Context, Template


def render_document_body(document_type, *, resident, issued_document):
    template = Template(document_type.template_body)
    context = Context({
        "resident": resident,
        "document": issued_document,
        "purpose": issued_document.purpose,
    })
    return template.render(context)
