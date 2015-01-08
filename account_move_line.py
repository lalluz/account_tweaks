# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class account_move_line (osv.Model):

    _inherit = 'account.move.line'

    def reconcile (self, cr, uid, ids, *args, **kwargs):
        res = super (account_move_line, self).reconcile (cr, uid, ids, *args, **kwargs)

        context = kwargs.get ('context')
        invoice_obj = self.pool.get ('account.invoice')
        lines = self.browse (cr, uid, ids, context=context)

        for line in lines:
            if not line.invoice:
                continue

            if invoice_obj.test_paid (cr, uid, [line.invoice.id]):
                invoice_obj.confirm_paid (cr, uid, [line.invoice.id])

        return res

    def list_category_to_reconcile (self, cr, uid, category, context=None):
        res = self.list_partners_to_reconcile (cr, uid, context=None)

        ids = [i[0] for i in res]
        partner_obj = self.pool.get ('res.partner')
        ids = partner_obj.search (cr, uid, [('id', 'in', ids), (category, '=', True)], context=context)

        return partner_obj.name_get (cr, uid, ids, context=context)

    def list_suppliers_to_reconcile (self, cr, uid, context=None):
        return self.list_category_to_reconcile (cr, uid, 'supplier', context=None)

    def list_customers_to_reconcile (self, cr, uid, context=None):
        return self.list_category_to_reconcile (cr, uid, 'customer', context=None)
