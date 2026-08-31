"""
Fills a DocumentType's template_body in with a specific recipient's data.

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
from dataclasses import dataclass, fields

from django.template import Context, Template

from residents.models import Resident


@dataclass
class WalkInSubject:
    """
    Stands in for a Resident when rendering a document for someone with no
    Resident record ("Print without an account"). Exposes the same
    attribute/method names a template_body would use on a real Resident
    (full_name, address, get_sex_display(), ...) so DocumentType authors
    never need to know or write around which path produced the document
    they're templating for -- one template body renders correctly either
    way.

    Not a Django model -- it's assembled fresh from IssuedDocument.
    walk_in_details at render time, never queried or saved on its own.
    """

    full_name: str
    address: str = ""
    resident_id: str = ""
    birth_date: str = ""
    sex: str = ""
    civil_status: str = ""
    purok_or_sitio: str = ""
    contact_number: str = ""

    def get_sex_display(self):
        return dict(Resident.Sex.choices).get(self.sex, self.sex)

    def get_civil_status_display(self):
        return dict(Resident.CivilStatus.choices).get(self.civil_status, self.civil_status)


_WALK_IN_FIELDS = {f.name for f in fields(WalkInSubject)}


def build_subject(issued_document):
    """
    Returns whatever should stand in for {{ resident }} when rendering
    issued_document's body: the real Resident if there is one, otherwise
    a WalkInSubject built from walk_in_details.
    """
    if issued_document.resident_id:
        return issued_document.resident
    details = issued_document.walk_in_details or {}
    return WalkInSubject(**{k: v for k, v in details.items() if k in _WALK_IN_FIELDS})


def render_document_body(document_type, *, resident, issued_document):
    template = Template(document_type.template_body)
    context = Context({
        "resident": resident,
        "document": issued_document,
        "purpose": issued_document.purpose,
    })
    return template.render(context)
