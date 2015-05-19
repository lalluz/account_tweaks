# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class account_invoice (osv.Model):

    _inherit = 'account.invoice'

    def onchange_company_id (self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id, context=None):
        res = super (account_invoice, self).onchange_company_id (
            cr, uid, ids, company_id, part_id, type, invoice_line, currency_id, context=context)

        settings_obj = self.pool.get ('account.config.settings')

        settings = settings_obj.browse (cr, uid, settings_obj.search (
            cr, uid, [('company_id', '=', company_id)]))

        if type == 'out_invoice':
            journal_id = 1
            if settings and settings[0].sale_journal_id:
                journal_id = settings[0].sale_journal_id.id
        elif type == 'out_refund':
            journal_id = 3
            if settings and settings[0].sale_refund_journal_id:
                journal_id = settings[0].sale_refund_journal_id.id
        elif type == 'in_invoice':
            journal_id = 2
            if settings and settings[0].purchase_journal_id:
                journal_id = settings[0].purchase_journal_id.id
        elif type == 'in_refund':
            journal_id = 4
            if settings and settings[0].purchase_refund_journal_id:
                journal_id = settings[0].purchase_refund_journal_id.id

        if journal_id:
            res['value']['journal_id'] = journal_id

        return res

    def _get_day (self, cr, uid, ids, prop, arg, context):
        invoice_obj = self.pool.get ('account.invoice')

        res = {}
        for invoice in invoice_obj.browse (cr, uid, ids):
            res[invoice.id] = invoice.date_invoice

        return res

    def _get_projects (self, cr, uid, ids, prop, arg, context):
        project_obj = self.pool.get ('project.project')
        projects = project_obj.browse (cr, uid, project_obj.search (cr, uid, []))
        project_map = dict ([(p.analytic_account_id.id, p.id) for p in projects])

        res = {}
        for invoice in self.browse (cr, uid, ids):
            res[invoice.id] = []

            for line in invoice.invoice_line:
                account = line.account_analytic_id

                if account.type != 'contract' and account.parent_id:
                    if account.parent_id.type == 'contract':
                        account = account.parent_id

                project_id = project_map.get (account.id) # FIXME
                if project_id:
                    res[invoice.id].append (project_id)

        return res

    def _search_projects (self, cr, uid, obj, name, args, context=None):
        project_obj = self.pool.get ('project.project')
        invoice_line_obj = self.pool.get ('account.invoice.line')
        analytic_account_obj = self.pool.get ('account.analytic.account')

        search_set = search_not_set = False

        pargs = [('name', a[1], a[2]) for a in args]
        for arg in args:
            if arg[2] == False:
                if arg[1] == '=':
                    search_not_set = True
                elif arg[1] == '!=':
                    search_set = True

        projects = project_obj.browse (cr, uid, project_obj.search (cr, uid, pargs))
        project_analytic_ids = [p.analytic_account_id.id for p in projects \
                                if p.analytic_account_id]

        account_ids = analytic_account_obj.search (cr, uid, [
            ('|'),
            ('id', 'in', project_analytic_ids),
            ('parent_id', 'in', project_analytic_ids),
        ])

        invoice_lines = invoice_line_obj.browse (cr, uid, invoice_line_obj.search (
            cr, uid, [('account_analytic_id', 'in', account_ids)])
        )

        if search_set:
            invoice_lines = invoice_line_obj.browse (cr, uid, invoice_line_obj.search (
                cr, uid, [('account_analytic_id', '!=', False)])
            )

        if search_not_set:
            invoice_lines = invoice_line_obj.browse (cr, uid, invoice_line_obj.search (
                cr, uid, [('account_analytic_id', '=', False)])
            )

        return [('id', 'in', [l.invoice_id.id for l in invoice_lines])]

    def _get_move_line_ids (self, cr, uid, ids, prop, arg, context):
        res = {}
        for invoice in self.browse (cr, uid, ids):
            res[invoice.id] = []
            if invoice.move_id and invoice.move_id.line_id:
                res[invoice.id] = [m.id for m in invoice.move_id.line_id]

        return res

    def _get_partners (self, cr, uid, ids, context={}):
        invoice_obj = self.pool.get ('account.invoice')

        return invoice_obj.search (cr, uid, [
            '|', ('partner_id', 'in', ids), ('sending_partner_id', 'in', ids),
        ])

    def _get_mails (self, cr, uid, ids, context={}):
        mail_obj = self.pool.get ('mail.mail')
        message_obj = self.pool.get ('mail.message')

        mails = mail_obj.browse (cr, uid, ids)

        message_ids = message_obj.browse (cr, uid, message_obj.search (cr, uid, [
            ('id', 'in', [m.mail_message_id.id for m in mails]),
            ('model', '=', 'account.invoice'),
        ]))

        return [m.res_id for m in message_ids]

    def _get_sending_results (self, cr, uid, ids, prop, arg, context):
        invoice_obj = self.pool.get ('account.invoice')

        mail_obj = self.pool.get ('mail.mail')
        message_obj = self.pool.get ('mail.message')

        message_ids = message_obj.search (cr, uid, [
            ('res_id', 'in', ids),
            ('model', '=', 'account.invoice'),
        ])

        mails = mail_obj.browse (cr, uid, mail_obj.search (cr, uid, [
            ('mail_message_id', 'in', message_ids),
        ]))

        mail_map = {}
        for mail in mails:
            mail_map.setdefault (mail.res_id, []).append (mail)

        res = {}
        for invoice in invoice_obj.browse (cr, uid, ids):
            sent_emails = mail_map.get (invoice.id, [])
            sending_state = 'NOT_SENT'

            if [m for m in sent_emails if m.state == 'sent']:
                sending_state = 'SENT'
            elif [m for m in sent_emails if m.state == 'outgoing']:
                sending_state = 'OUTGOING'
            elif [m for m in sent_emails if m.state == 'exception']:
                sending_state = 'ERROR'

            if not sent_emails or sending_state in ['NOT_SENT', 'ERROR']:
                if invoice.manual_sending:
                    sending_state = 'TO_SEND_MANUALLY'
                else:
                    if invoice.sending_partner_id:
                        if not invoice.sending_partner_id.email:
                            sending_state = 'MISSING_RECIPIENTS'
                    elif not invoice.partner_id.email:
                        sending_state = 'MISSING_RECIPIENTS'

                if invoice.sent_manually:
                    sending_state = 'MANUALLY_SENT'

            # allow to set invoices as "SENT" even if the email machinery has
            # been circumvented for any reason
            if not sent_emails and invoice.sent:
                sending_state = 'SENT'

            recipients = []
            if invoice.sending_partner_id and invoice.sending_partner_id.email:
                recipients = [invoice.sending_partner_id.email]
            elif invoice.partner_id and invoice.partner_id.email:
                recipients = [invoice.partner_id.email]

            res[invoice.id] = {
                'sending_state': sending_state,
                'sent_emails': [m.id for m in sent_emails],
                'recipients': ', '.join (recipients),
            }

        return res

    SENDING_STATES = [
        ('NOT_SENT', _('Not Sent').replace (' ', u'\u00a0')),
        ('SENT', _('Sent').replace (' ', u'\u00a0')),
        ('OUTGOING', _('Outgoing').replace (' ', u'\u00a0')),
        ('ERROR', _('Error').replace (' ', u'\u00a0')),
        ('MANUALLY_SENT', _('Sent Manually').replace (' ', u'\u00a0')),
        ('TO_SEND_MANUALLY', _('Manual').replace (' ', u'\u00a0')),
        ('MISSING_RECIPIENTS', _('Missing Recipients').replace (' ', u'\u00a0')),
    ]

    _columns = {
        'move_line_ids': fields.function (_get_move_line_ids, relation='account.move.line',
                                          string='Journal Items', type="one2many", readonly=True),
        'sending_partner_id': fields.many2one ('res.partner', string='Receiving Partner', ondelete='set null'),
        'heading_partner_id': fields.many2one ('res.partner', string='Heading Partner', ondelete='set null'),
        'project_id': fields.many2one ('project.project', string='Project', ondelete='restrict'),
        'projects': fields.function (_get_projects, relation='project.project',
                                     string='Projects', type="many2many",
                                     fnct_search=_search_projects, readonly=True),
        'date_invoice_supplier': fields.date ('Supplier Invoice Date', select=True),
        'with_fiscal_stamp': fields.boolean ('Bollo'),
        'with_split_payment': fields.boolean ('Scissione dei Pagamenti'),

        'manual_sending': fields.boolean ("Manual Sending"),
        'sent_manually': fields.boolean ("Sent Manually"),
        'sending_state': fields.function (
            _get_sending_results, string='Sending State',
            multi='sending_results', type="selection", selection=SENDING_STATES, store={
                'account.invoice': (lambda self, cr, uid, ids, context={}: ids, [], 10),
                'mail.mail': (_get_mails, [], 10),
                'res.partner': (_get_partners, ['email'], 10),
            }),
        'sent_emails': fields.function (
            _get_sending_results, string='Sent Emails',
            multi='sending_results', type="one2many", relation='mail.mail', readonly=True),
        'recipients': fields.function (
            _get_sending_results, string='Recipients',
            multi='sending_results', type="text", readonly=True),

        'day_invoice': fields.function (_get_day, string='Day', type="char", store=True),
    }

    _sql_constraints = [
        ('unique_supplier_invoice', 'unique(partner_id, supplier_invoice_number, date_invoice_supplier)',
         'An invoice with the same date and number exists for this supplier'),
    ]

    def copy (self, cr, uid, id, default={}, context=None):
        default.update ({
            'supplier_invoice_number': False,
            'date_invoice_supplier': False,
        })

        return super (account_invoice, self).copy(cr, uid, id, default, context)

    def unlink_validated (self, cr, uid, ids, context={}):
        # FIXME: should delete also payments which have been inserted as
        # journal entries (not as "Customer payments" ==> vouchers) and are
        # reconciled

        invoice = self.browse (cr, uid, ids[0], context=context)

        if not invoice.move_id:
            return

        payments = invoice.payment_ids

        osv.osv.unlink (self, cr, uid, invoice.id)
        osv.osv.unlink (self.pool.get ('account.move'), cr, uid, invoice.move_id.id)

        moves = set ([p.move_id for p in payments if p.move_id])
        vouchers = set (sum ([m.voucher_ids for m in moves], []))
        reconciles = set ([p.reconcile_id for p in payments if p.reconcile_id])
        reconciles.union (set ([p.reconcile_partial_id for p in payments if p.reconcile_partial_id]))

        for r in reconciles:
            osv.osv.unlink (self.pool.get ('account.move.reconcile'), cr, uid, r.id)

        for m in moves:
            osv.osv.unlink (self.pool.get ('account.move'), cr, uid, m.id)

        for v in vouchers:
            osv.osv.unlink (self.pool.get ('account.voucher'), cr, uid, v.id)

        action = {
            'out_invoice': 'action_invoice_tree',
            'out_refund': 'action_invoice_tree3',
            'in_invoice': 'action_invoice_tree2',
            'in_refund': 'action_invoice_tree4',
        }[invoice.type]

        act_model, act_id = self.pool.get ('ir.model.data').get_object_reference (
            cr, uid, 'account', action)

        return self.pool.get ('ir.actions.act_window').read (cr, uid, act_id)

    def onchange_sending_partner_id (self, cr, uid, ids, partner_id, sending_partner_id):
        partner_obj = self.pool.get ('res.partner')
        invoice_obj = self.pool.get ('account.invoice')

        partner = partner_obj.browse (cr, uid, partner_id)

        sending_partner = None
        if sending_partner_id:
            sending_partner = partner_obj.browse (cr, uid, sending_partner_id)

        recipients = partner.email
        if sending_partner and sending_partner.email:
            recipients = sending_partner.email

        sending_state = None
        if ids:
            invoice = invoice_obj.browse (cr, uid, ids[0])

            sending_state = invoice.sending_state
            if not recipients:
                sending_state = 'MISSING_RECIPIENTS'

        return {'value': {'recipients': recipients, 'sending_state': sending_state}}

    def invoice_print (self, cr, uid, ids, context=None):
        '''Don't mark invoice as sent.'''
        res = super (account_invoice, self).invoice_print (cr, uid, ids, context=context)

        self.write (cr, uid, ids, {'sent': False}, context=context)

        return res

    def do_drop_document (self, cr, uid, ids, context=None):
        attachment_obj = self.pool.get ('ir.attachment')

        invoices = self.browse (cr, uid, ids)
        invoice_ids = [i.id for i in invoices]  # if i.state not in ['SENT', 'MANUALLY_SENT']]

        res = attachment_obj.search (cr, uid, [('res_model', '=', 'account.invoice'), ('res_id', 'in', invoice_ids)])
        attachment_obj.unlink (cr, SUPERUSER_ID, res)

    def action_invoice_sent (self, cr, uid, ids, context=None):
        res = super (account_invoice, self).action_invoice_sent (cr, uid, ids, context=context)

        res['context']['default_composition_mode'] = 'mass_mail'
        res['context']['default_same_thread'] = False

        template_obj = self.pool.get ('email.template')

        template = template_obj.browse (cr, uid, res['context']['default_template_id'])

        if not template.reply_to:
            res['context']['default_reply_to'] = template.email_from

        return res

    def invoice_pay_customer (self, cr, uid, ids, context=None):
        res = super (account_invoice, self).invoice_pay_customer (cr, uid, ids, context=context)

        invoice = self.browse(cr, uid, ids[0], context=context)

        if invoice.type in ['out_invoice', 'out_refund']:
            res['context']['default_date'] = invoice.date_invoice

        return res

#    def fields_view_get (self, cr, uid, view_id=None, view_type=False,
#                         context=None, toolbar=False, submenu=False):
#        res = super (account_invoice, self).fields_view_get (
#            cr, uid, view_id=view_id, view_type=view_type, context=context,
#            toolbar=toolbar, submenu=submenu)
#
#        if not res.get ('toolbar'):
#            return res
#
#        act_model, act_id = self.pool.get ('ir.model.data').get_object_reference (
#            cr, uid, 'account_tweaks', 'action_delete_validated_invoice')
#
#        if view_type == 'form':
#            for action in res['toolbar']['relate'][:]:
#                if action['id'] == act_id and uid != SUPERUSER_ID:
#                    res['toolbar']['relate'].remove (action)
#
#        return res


class account_invoice_line (osv.Model):

    _inherit = 'account.invoice.line'

    def product_id_change (self, cr, uid, ids, product, uom_id, *args, **kwargs):
        res = super (account_invoice_line, self).product_id_change (
            cr, uid, ids, product, uom_id, *args, **kwargs)

        context = kwargs.get ('context')

        product = self.pool.get('product.product').browse (cr, uid, product, context=context)

        if product.id and product.property_analytic_account_income.id:
            res['value']['account_analytic_id'] = product.property_analytic_account_income.id
        else:
            res['value']['account_analytic_id'] = None

        return res
