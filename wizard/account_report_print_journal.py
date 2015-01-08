# -*- coding: utf-8 -*-

from openerp.osv import fields
from openerp.osv import osv

from lxml import etree

import datetime


class account_print_journal (osv.osv_memory):
    _inherit = 'account.print.journal'

    def _get_period (self, cr, uid, context=None):
        period_obj = self.pool.get ('account.period')

        today = datetime.date.today ()
        previous = datetime.date (today.year, today.month, 1) - datetime.timedelta (days=1)
        code = previous.strftime ('%02m/%Y')

        return period_obj.search (cr, uid, [('code', '=', code)])[0]

    def onchange_filter (self, cr, uid, ids, *args, **kwargs):
        res = super (account_print_journal, self).onchange_filter (self, cr, uid, ids, *args, **kwargs)

        period_obj = self.pool.get ('account.period')
        code = datetime.date.today ().strftime ('%02m/%Y')

        period_id = self._get_period (cr, uid)

        res['value']['period_from'] = period_id
        res['value']['period_from'] = period_id

        return res

    _columns = {
        'merge_journals': fields.boolean ('Merge Journals'),
    }

    _defaults = {
        'merge_journals': True,
        'period_from': _get_period,
        'period_to': _get_period,
        'target_move': 'all',
    }

    def fields_view_get (self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super (account_print_journal, self).fields_view_get (cr, uid,
                     view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        domain = None
        if context.get ('sale_only'):
            domain = "[('type', 'in', ('sale', 'sale_refund'))]"
        elif context.get ('purchase_only'):
            domain = "[('type', 'in', ('purchase', 'purchase_refund'))]"

        if domain:
            doc = etree.XML (res['arch'])
            nodes = doc.xpath ("//field[@name='journal_ids']")
            for node in nodes:
                node.set ('domain', domain)
            res['arch'] = etree.tostring (doc)

        return res

    def _print_report (self, cr, uid, ids, data, context=None):
        data['form'].update (self.read(cr, uid, ids, ['merge_journals'], context=context)[0])

        res = super (account_print_journal, self)._print_report (cr, uid, ids, data, context=context)

        if res['report_name'] == 'account.journal.period.print.sale.purchase':
            res['report_name'] = 'account_tweaks.journal.period.print.sale.purchase'

        return res

