# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class account_config_settings (osv.osv_memory):

    _inherit = 'account.config.settings'

    # Fix bug in default implementation
    def onchange_company_id (self, cr, uid, ids, company_id, context=None):
        res = super (account_config_settings, self).onchange_company_id (cr, uid, ids, company_id, context=None)

        settings_obj = self.pool.get ('account.config.settings')
        settings_ids = settings_obj.search (cr, uid, [('company_id', '=', company_id)])

        if settings_ids:
            settings = settings_obj.browse (cr, uid, settings_ids)[0]

            if settings.sale_journal_id.sequence_id:
                sale_sequence = settings.sale_journal_id.sequence_id

                res['value'].update ({
                    'sale_sequence_prefix': sale_sequence.prefix,
                    'sale_sequence_next': sale_sequence.number_next,
                })

            if settings.sale_refund_journal_id.sequence_id:
                sale_refund_sequence = settings.sale_refund_journal_id.sequence_id

                res['value'].update ({
                    'sale_refund_sequence_prefix': sale_refund_sequence.prefix,
                    'sale_refund_sequence_next': sale_refund_sequence.number_next,
                })

            if settings.purchase_journal_id.sequence_id:
                purchase_sequence = settings.purchase_journal_id.sequence_id

                res['value'].update ({
                    'purchase_sequence_prefix': purchase_sequence.prefix,
                    'purchase_sequence_next': purchase_sequence.number_next,
                })

            if settings.purchase_refund_journal_id.sequence_id:
                purchase_refund_sequence = settings.purchase_refund_journal_id.sequence_id

                res['value'].update ({
                    'purchase_refund_sequence_prefix': purchase_refund_sequence.prefix,
                    'purchase_refund_sequence_next': purchase_refund_sequence.number_next,
                })

        return res
