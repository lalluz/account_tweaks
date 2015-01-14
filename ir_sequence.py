# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class ir_sequence(osv.Model):

    _inherit = 'ir.sequence'

    def _is_child(self, cr, uid, ids, field_name, arg, context=None):
        sequence_fiscalyear_obj = self.pool.get('account.sequence.fiscalyear')

        res = {}

        for sequence in self.browse(cr, uid, ids, context=context):
            children = sequence_fiscalyear_obj.search(
                cr, uid, [('sequence_id', '=', sequence.id)])

            res[sequence.id] = True if children else False

        return res

    _columns = {
        'auto_fiscalyears': fields.boolean('Automatically create '
                                           'fiscal year sequences'),
        'fiscalyear': fields.char('Fiscal Year', required=False, size=4),
        'is_child': fields.function(_is_child, string='Is Child Sequence',
                                    store=True, type='boolean'),
    }

    _defaults = {
        'auto_fiscalyears': False,
    }

    def update_fiscalyears(self, cr, uid, ids, context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        sequence_fiscalyear_obj = self.pool.get('account.sequence.fiscalyear')

        fiscal_years = fiscalyear_obj.browse(
            cr, uid, fiscalyear_obj.search(cr, uid, [], order='code'))

        for sequence in self.browse(cr, uid, ids, context=context):
            existing_years = [f.fiscalyear_id.code
                              for f in sequence.fiscal_ids]

            for i, year in enumerate(fiscal_years):
                if year.code in existing_years:
                    continue

                sequence_id = self.create(cr, uid, {
                    'code': sequence.code,
                    'name': '%s %s' % (sequence.name, year.code),
                    'prefix': sequence.prefix.replace('%(year)s', year.code),
                    'suffix': sequence.suffix,
                    'number_next': 1,
                    'number_increment': sequence.number_increment,
                    'implementation': sequence.implementation,
                    'padding': sequence.padding,
                    'active': True,
                    'auto_fiscalyears': False,
                    'fiscalyear': year.code,
                    'company_id': sequence.company_id.id,
                })

                if i == 0:
                    self.write(cr, uid, sequence_id, {
                        'number_next': sequence.number_next,
                    })

                sequence_fiscalyear_obj.create(cr, uid, {
                    'sequence_id': sequence_id,
                    'sequence_main_id': sequence.id,
                    'fiscalyear_id': year.id,
                })

                self.write(cr, uid, sequence_id, {
                    'is_child': True,
                })

    def write(self, cr, uid, ids, values, context=None):
        ret = super(ir_sequence, self).write(cr, uid, ids, values, context)

        if values.get('auto_fiscalyears'):
            self.update_fiscalyears(cr, uid, ids, context)

        return ret
