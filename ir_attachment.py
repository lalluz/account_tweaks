# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class ir_attachment (osv.Model):

    _inherit = 'ir.attachment'

    def can_be_deleted (self, cr, uid, ids, context=None):
        if uid == SUPERUSER_ID:
            return True

        attach = self.browse (cr, uid, ids, context=context)
        if attach.res_model != 'account.invoice':
            return True

        item_obj = self.pool.get (attach.res_model)
        item = item_obj.browse (cr, uid, attach.res_id, context=context)

        if item.type in ['out_invoice', 'out_refund']:
            return False

        return True

    def unlink (self, cr, uid, ids, context=None):
        if isinstance (ids, (int, long)):
            ids = [ids]

        delete_ids = ids[:]
        for i in ids:
            if not self.can_be_deleted (cr, uid, i, context):
                delete_ids.remove (i)

        return super (ir_attachment, self).unlink (cr, uid, delete_ids, context)
