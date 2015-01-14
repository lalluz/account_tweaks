{
    'name': 'Account Tweaks - Goodora',
    'description': 'Tweaks for account module by Goodora s.r.l.',
    'author': 'Goodora s.r.l.',
    'version': '0.1',
    'category': 'Hidden',
    'depends': [
        'web',
        'account',
        'account_voucher',
        'project',
    ],
    'js': ['static/src/js/account_tweaks.js'],
    'qweb': ['static/src/xml/account_move_reconciliation.xml'],
    'data': [
        'account_view.xml',
        'account_invoice_view.xml',
        'product_view.xml',
        'account_report.xml',
        'ir_sequence_view.xml',
        'account_invoice_sequence_data.xml',
        'wizard/account_report_print_journal_view.xml',
        'exports/export_invoice.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}

