# -*- coding: utf-8 -*-

from openerp.addons.account.wizard.account_reconcile import account_move_line_reconcile


class this_account_move_line_reconcile (account_move_line_reconcile):

    def trans_rec_reconcile_full (self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool.get ('account.move.line')

        ret = super (this_account_move_line_reconcile, self).trans_rec_reconcile_full (
            cr, uid, ids, context=context)

        lines = account_move_line_obj.browse (cr, uid, context['active_ids'])
#        for line in lines:
#            if line.invoice and line.invoice.test_paid ():
#                 line.invoice.confirm_paid ()

        return ret

