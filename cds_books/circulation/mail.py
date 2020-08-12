from invenio_app_ils.circulation.mail.messages import LoanListMessage


def loan_list_message_creator(patron, loans, message_ctx, **kwargs):
    """Loan list message creator."""
    return LoanListMessage(patron, loans, message_ctx, footer_template="cds_librarian_footer", **kwargs)
