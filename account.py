# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

import openerp.addons.decimal_precision as dp

from openerp.tools.translate import _

from collections import OrderedDict


class account_account (osv.Model):

    _inherit = 'account.account'

    _columns = {
        'account_type_name': fields.related('user_type', 'name', type='char', string='Account Type'),
    }


class account_journal (osv.Model):

    _inherit = 'account.journal'

    _columns = {
        'invoice_footer': fields.text ('invoice_footer', help="Invoice Footer")
    }


class account_move (osv.Model):

    _name = 'account.move'
    _inherit = ['account.move', 'mail.thread']

    _columns = {
        'voucher_ids': fields.one2many ('account.voucher', 'move_id', 'Vouchers'),
        'state': fields.selection ([('draft', 'Unposted'), ('posted', 'Posted')],
                                   'Status', required=True, readonly=True,
                                   track_visibility='onchange'),
    }

    def unpost (self, cr, uid, ids, context={}):
        move = self.browse (cr, uid, ids[0], context=context)

        move.write ({'state': 'draft'})


class account_voucher (osv.Model):

    _inherit = 'account.voucher'

    def unlink_validated (self, cr, uid, ids, context={}):
        voucher = self.browse (cr, uid, ids[0], context=context)

        if not voucher.move_id:
            return

        reconciles = set ([l.reconcile_id for l in voucher.move_id.line_id if l.reconcile_id])
        reconciles.union (set ([l.reconcile_partial_id for l in voucher.move_id.line_id if l.reconcile_partial_id]))

        invoices = []
        for r in reconciles:
            invoices += [l.invoice for l in r.line_id if l.invoice]
            osv.osv.unlink (self.pool.get ('account.move.reconcile'), cr, uid, r.id)

        osv.osv.unlink (self, cr, uid, voucher.id)
        osv.osv.unlink (self.pool.get ('account.move'), cr, uid, voucher.move_id.id)

        for invoice in invoices:
            if not self.pool.get ('account.invoice').test_paid (cr, uid, [invoice.id]):
                invoice.write ({'state': 'open'})

        action = {
            'receipt': 'action_vendor_receipt',
            'payment': 'action_vendor_payment',
        }[voucher.type]

        act_model, act_id = self.pool.get ('ir.model.data').get_object_reference (
            cr, uid, 'account_voucher', action)

        return self.pool.get ('ir.actions.act_window').read (cr, uid, act_id)


class account_tax_code (osv.Model):

    _inherit = 'account.tax.code'

    _columns = {
        'exclude_from_company_vs_private': fields.boolean(
            'exclude_from_company_vs_private')
    }

    _defaults = {
        'exclude_from_company_vs_private': False,
    }


class account_tax (osv.Model):

    _inherit = 'account.tax'

    _columns = {
        'with_split_payment': fields.boolean('with_split_payment'),
    }

    _defaults = {
        'with_split_payment': False,
    }


class account_fiscalyear (osv.Model):

    _inherit = 'account.fiscalyear'

    _columns = {
        'prorata': fields.float ('prorata', digits_compute=dp.get_precision('Account'), required=True)
    }

    _defaults = {
        'prorata': 17,  # FIXME: placeholder
    }

    def create(self, cr, uid, vals, context=None):
        ret = super(account_fiscalyear, self).create(cr, uid, vals, context)

        sequence_obj = self.pool.get('ir.sequence')

        ids = sequence_obj.search( cr, uid, [('auto_fiscalyears', '=', True)])
        sequence_obj.update_fiscalyears(cr, uid, ids, context)

        return ret


class account_period (osv.Model):

    _inherit = 'account.period'

    def _previous (self, cr, uid, ids, field_name, arg, context=None):
        res = {}

        for period in self.browse (cr, uid, ids, context=context):
            prev_ids = self.search (cr, uid, [
                ('date_start', '<', period.date_start),
                ('special', '=', False),
            ])

            if prev_ids:
                res[period.id] = self.browse (cr, uid, [prev_ids[-1]], context=context)[-1]
            else:
                res[period.id] = None

        return res

    def _total_previous_74ter_credit (self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = {}

        for period in self.browse (cr, uid, ids, context=context):
            total_previous_74ter_credit = 0
            p = period
            while p.previous and (p.previous.amount_74ter_cee <= 0):
                total_previous_74ter_credit += p.previous.amount_74ter_cee
                p = p.previous

                if int (p.fiscalyear_id.name) < 2014:  # FIXME: hack
                    break

            total_previous_74ter_vat = total_previous_74ter_credit \
                / (100 + period.tax_rate_74ter) * period.tax_rate_74ter
            net_vat_74ter = period.gross_vat_74ter + total_previous_74ter_vat

            res[period.id] = OrderedDict ([
                ('total_previous_74ter_credit', total_previous_74ter_credit),
                ('total_previous_74ter_vat', total_previous_74ter_vat),
                ('net_vat_74ter', net_vat_74ter),
            ])

        return res

    def _previous_74ter_credit (self, cr, uid, ids, field_name, arg, context=None):
        res = {}

        for period in self.browse (cr, uid, ids, context=context):
            prev_ids = self.search (cr, uid, [
                ('date_start', '<', period.date_start),
                ('special', '=', False),
            ])

            if prev_ids:
                res[period.id] = self.browse (cr, uid, [prev_ids[-1]], context=context)[-1].amount_74ter_cee
            else:
                res[period.id] = None

        return res

    def _compute_liquidazione (self, cr, uid, ids, field_name, arg, context={}):
        tax_code_obj = self.pool.get ('account.tax.code')

        res = {}

        for period in self.browse (cr, uid, ids, context=context):
            ctx = {
                'period_id': period.id,
                'state': context.get ('state', 'all'),
            }

            credit_vat_amount = tax_code_obj.browse (
                cr, uid, tax_code_obj.search (cr, uid, [('code', '=', 'IVC')]))[0]._sum_period (None, None, ctx).values ()[0]
            credit_n_vat_amount = tax_code_obj.browse (
                cr, uid, tax_code_obj.search (cr, uid, [('code', '=', 'IVCN')]))[0]._sum_period (None, None, ctx).values ()[0]
            debit_vat_amount = tax_code_obj.browse (
                cr, uid, tax_code_obj.search (cr, uid, [('code', '=', 'IVD')]))[0]._sum_period (None, None, ctx).values ()[0]

            credit_prorata_vat_amount = credit_vat_amount * period.fiscalyear_id.prorata / 100

            credit_74ter_cee = tax_code_obj.browse (
                cr, uid, tax_code_obj.search (cr, uid, [('code', '=', 'IVC0I-74-ter-cee')]))[0]._sum_period (None, None, ctx).values ()[0]
            debit_74ter_cee = tax_code_obj.browse (
                cr, uid, tax_code_obj.search (cr, uid, [('code', '=', 'IVD0I-74-ter-cee')]))[0]._sum_period (None, None, ctx).values ()[0]
            amount_74ter_cee = debit_74ter_cee + credit_74ter_cee

            gross_vat_74ter = amount_74ter_cee / (100 + period.tax_rate_74ter) * period.tax_rate_74ter

            res[period.id] = OrderedDict ([
                ('credit_vat_amount', credit_vat_amount),
                ('credit_n_vat_amount', credit_n_vat_amount),
                ('credit_prorata_vat_amount', credit_prorata_vat_amount),
                ('debit_vat_amount', debit_vat_amount),
                ('credit_74ter_cee', credit_74ter_cee),
                ('debit_74ter_cee', debit_74ter_cee),
                ('amount_74ter_cee', amount_74ter_cee),
                ('gross_vat_74ter', gross_vat_74ter),
            ])

        return res

    _columns = {
        'tax_rate_74ter': fields.float ('tax_rate_74ter', digits_compute=dp.get_precision('Account'), required=True),

        'credit_vat_amount': fields.function (_compute_liquidazione, multi='compute'),
        'credit_n_vat_amount': fields.function (_compute_liquidazione, multi='compute'),
        'credit_prorata_vat_amount': fields.function (_compute_liquidazione, multi='compute'),
        'debit_vat_amount': fields.function (_compute_liquidazione, multi='compute'),
        'credit_74ter_cee': fields.function (_compute_liquidazione, multi='compute'),
        'debit_74ter_cee': fields.function (_compute_liquidazione, multi='compute'),
        'amount_74ter_cee': fields.function (_compute_liquidazione, multi='compute'),
        'gross_vat_74ter': fields.function (_compute_liquidazione, multi='compute'),

        'previous_74ter_credit': fields.function (_previous_74ter_credit),
        'total_previous_74ter_credit': fields.function (_total_previous_74ter_credit, multi='total_74ter_credit'),
        'total_previous_74ter_vat': fields.function (_total_previous_74ter_credit, multi='total_74ter_credit'),

        'net_vat_74ter': fields.function (_total_previous_74ter_credit, multi='total_74ter_credit'),

        'previous': fields.function (_previous),
    }

    _defaults = {
        'tax_rate_74ter': 22,
    }
