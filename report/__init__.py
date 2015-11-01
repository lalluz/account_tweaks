# -*- coding: utf-8 -*-

from openerp.report import report_sxw
from openerp.addons.account.report.account_journal import journal_print as account_journal_print
from openerp.addons.account.report.account_print_invoice import account_invoice as account_print_invoice

from collections import OrderedDict

from openerp.tools.translate import _


class TaxLine (object):

    def __init__ (self, **kwargs):
        self.ref = kwargs.get ('ref')
        self.move_id = kwargs.get ('move_id')
        self.journal_id = kwargs.get ('journal_id')
        self.date = kwargs.get ('date')
        self.invoice = kwargs.get ('invoice')
        self.account_tax_id = kwargs.get ('account_tax_id')
        self.tax_code_id = kwargs.get ('tax_code_id')
        self.tax_amount = kwargs.get ('tax_amount')
        self.debit = kwargs.get ('debit')
        self.credit = kwargs.get ('credit')
        self.is_last_line = False


class journal_print (account_journal_print):

    def __init__ (self, cr, uid, name, context=None):
        super (journal_print, self).__init__ (cr, uid, name, context=context)

        self.merge_journals = False
        self._totals = {}
        self._totals_template = {
            'base_amount': 0,
            'tax_amount': 0,
            'gross_amount': 0,
        }

        self.partial_gross_amount = 0

        self.localcontext.update ({
            'merge_journals': self._merge_journals,
            'tax_lines': self.tax_lines,
            'is_first_move_id': self.is_first_move_id,
            'is_last_line': self.is_last_line,
            'is_tax_line': self.is_tax_line,
            'get_gross_amount': self.get_gross_amount,
            'get_base_amount': self.get_base_amount,
            'get_tax_amount': self.get_tax_amount,
            'get_journal_names': self.get_journal_names,
            'get_number': self.get_number,
            'get_document_date': self.get_document_date,
            'get_document_number': self.get_document_number,
            'get_header': self.get_header,
            'get_totals': self.get_totals,
            'get_final_total': self.get_final_total,
            'get_partial_gross_amount': lambda: self.partial_gross_amount,
        })

    def _merge_journals (self):
        return self.merge_journals

    def set_context (self, objects, data, ids, report_type=None):
        ret = super (journal_print, self).set_context (objects, data, ids, report_type=report_type)

        self.merge_journals = data['form'].get ('merge_journals')
        if self.merge_journals:
            objects = []
            periods = data['form']['periods'][:]
            for obj in self.objects:
                if obj.period_id.id in periods:
                    objects.append (obj)
                    periods.remove (obj.period_id.id)

            self.localcontext['objects'] = self.objects = objects

        return ret

    def get_header (self, line):
        supplier_name = line.move_id.partner_id.name
        if not supplier_name:
            for l in line.move_id.line_id:
                if l.partner_id.name:
                    supplier_name = l.partner_id.name
                    break

        header = '%s - %s' % (
            line.move_id.partner_id.property_account_payable.code \
                if line.move_id.journal_id.type in ['purchase', 'purchase_refund'] \
                else line.move_id.partner_id.property_account_receivable.code,
            supplier_name,
        )

        return header

    def get_document_number (self, line):
        if not line.invoice:
            return line.move_id.alawin_num_documento # FIXME: hack

        if line.invoice.type in ['out_invoice', 'out_refund']:
            if line.journal_id and '74' in line.journal_id.name: # FIXME: hack
                return '%d/74ter' % self.get_number (line)

            return self.get_number (line) # FIXME

        return line.invoice.supplier_invoice_number

    def get_document_date (self, line):
        if not line.invoice:
            return '-'.join (line.move_id.alawin_data_documento.split ('-')[::-1]) # FIXME: hack

        if line.invoice.type in ['out_invoice', 'out_refund']:
            return self.formatLang (line.invoice.date_invoice, date=True)

        return '-'.join (line.invoice.date_invoice.split ('-')[::-1])

    def get_number (self, line):
        if not line.move_id.name:
            return '*' + str (line.move_id.id)

        for name in [line.move_id.name, line.move_id.name.split ('/')[-1]]:
            try:
                return int (name)
            except ValueError:
                pass

        return line.move_id.name

    def lines (self, period_id, journal_id=False):
        line_map = OrderedDict ()

        if not self.merge_journals:
            _lines = super (journal_print, self).lines (period_id, journal_id)
        else:
            _lines = super (journal_print, self).lines (period_id, None)

        for line in _lines:
            if line.move_id not in line_map:
                line_map[line.move_id] = line.move_id.line_id

        return sum (line_map.values (), [])

    def tax_lines (self, period_id, journal_id=False):
        tax_line_map = OrderedDict ()

        if not self.merge_journals:
            _lines = super (journal_print, self).lines (period_id, journal_id)
        else:
            _lines = super (journal_print, self).lines (period_id, None)

        for line in _lines:
            if line.move_id not in tax_line_map:
                tax_map = {}
                for l in line.move_id.line_id:
                    if not self.is_tax_line (l):
                        continue

                    tax_line = tax_map.setdefault (l.account_tax_id, TaxLine (
                        ref=l.ref,
                        move_id=l.move_id,
                        journal_id=l.journal_id,
                        date=l.date,
                        invoice=l.invoice,
                        account_tax_id=l.account_tax_id,
                        tax_code_id=l.tax_code_id,
                        tax_amount=0,
                        debit=0,
                        credit=0,
                    ))

                    tax_line.tax_amount += l.debit or l.credit
                    tax_line.debit += l.debit
                    tax_line.credit += l.credit

                tax_line_map[line.move_id] = tax_map.values ()
                tax_line_map[line.move_id][-1].is_last_line = True

        return sum (tax_line_map.values (), [])

    def is_first_move_id (self, move_id):
        if not self.last_move_id or self.last_move_id != move_id:
            self.partial_gross_amount = 0
            return True

        return False

    def is_last_line (self, line):
        if line == line.move_id.line_id[-1]:
            return True

        return False

    def is_tax_line (self, line):
        if line.account_tax_id:
            return True

        if not line.tax_code_id:
            return False

        if line.invoice:
            if line.account_id.code.startswith ('8.'): # FIXME
                return False

            account_tax_obj = self.pool.get ('account.tax')
            tax_ids = account_tax_obj.search (self.cr, self.uid, [('base_code_id', '=', line.tax_code_id.id)])
            if tax_ids:
                line.account_tax_id = account_tax_obj.browse (self.cr, self.uid, tax_ids[0])
                return True

        return False

    def _match_tax_line_amount (self, line, amount):
        tax_code_ids = []
        if line.account_tax_id.tax_code_id:
            tax_code_ids.append (line.account_tax_id.tax_code_id)

        if line.account_tax_id.child_depend and line.account_tax_id.child_ids:
            tax_code_ids = [c.tax_code_id for c in line.account_tax_id.child_ids]

        l_amount = 0
        for l in line.move_id.line_id:
            if l.tax_code_id not in tax_code_ids:
                continue

            l_amount += self._get_result (l, l.debit or l.credit)

        if l_amount != amount and abs (l_amount - amount) =< 0.02: # FIXME: check me
            return l_amount

        return amount

    def _get_sign (self, line, result):
        if line.move_id.journal_id.type in ['sale', 'sale_refund']:
            if result < 0:
                sign = 1 if line.debit else -1
            else:
                sign = -1 if line.debit else 1

        elif line.move_id.journal_id.type in ['purchase', 'purchase_refund']:
            if result < 0:
                sign = 1 if line.credit else -1
            else:
                sign = -1 if line.credit else 1

        return sign

    def _get_result (self, line, result):
        # avoid returning "-0.00" result
        return 0 if result == 0 else result * self._get_sign (line, result)

    def get_gross_amount (self, line):
        account_tax_obj = self.pool.get ('account.tax')

        res = account_tax_obj.compute_all (self.cr, self.uid,
            [line.account_tax_id], line.tax_amount, 1)

        amount = self.get_base_amount (line, False) + self.get_tax_amount (line, False)

        self.partial_gross_amount += amount

        self._totals.setdefault (line.account_tax_id, dict (self._totals_template))['gross_amount'] += amount

        return amount

    def get_base_amount (self, line, update_total=True):
        account_tax_obj = self.pool.get ('account.tax')

        res = account_tax_obj.compute_all (self.cr, self.uid,
            [line.account_tax_id], line.tax_amount, 1)

        amount = self._get_result (line, res['total'])

        if update_total:
            self._totals.setdefault (
                line.account_tax_id,
                dict (self._totals_template))['base_amount'] += amount

        return amount

    def get_tax_amount (self, line, update_total=True):
        account_tax_obj = self.pool.get ('account.tax')

        res = account_tax_obj.compute_all (self.cr, self.uid,
            [line.account_tax_id], line.tax_amount, 1)

        amount = self._get_result (line, sum ([t['amount'] for t in res['taxes']]))
        amount = self._match_tax_line_amount (line, amount)

        if update_total:
            self._totals.setdefault (
                line.account_tax_id,
                dict (self._totals_template))['tax_amount'] += amount

        return amount

    def get_journal_names (self, obj):
        if not self.merge_journals:
            return obj.journal_id.name

        names = ',\n'.join (sorted ([j.name for j in self.pool.get ('account.journal').browse (
            self.cr, self.uid, list (self.journal_ids))]))

        return names

    def get_totals (self):
        return self._totals

    def get_final_total (self, key):
        return sum ([v[key] for v in self._totals.values ()])


report_sxw.report_sxw (
    'report.account_tweaks.journal.period.print.sale.purchase',
    'account.journal.period',
    'addons/account_tweaks/report/account_journal_sale_purchase.rml',
    parser=journal_print,
    header='external',
)


class account_invoice (report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super (account_invoice, self).__init__(cr, uid, name, context=context)

        self.localcontext.update ({
            'formatBreakline': self.formatBreakline,
        })

    def set_context (self, objects, data, ids, report_type=None):
        ret = super (account_invoice, self).set_context (objects, data, ids, report_type=report_type)

        invoice = self.localcontext['objects'][0]
        self.localcontext['company'].current_journal_code = invoice.journal_id.code

        self.localcontext['company'].rml_footer = invoice.journal_id.invoice_footer \
            or self.localcontext['company'].rml_footer

        self.localcontext['company'].partner_id.vat = invoice.journal_id.invoice_vat \
            or self.localcontext['company'].partner_id.vat

        return ret

    def formatBreakline (self, text):
        lines = self.format (text).split ('\n')
        for i, line in enumerate (lines[:]):
            if line == '':
                lines[i] = u'\u00a0'

        return '\n'.join (lines)


report_sxw.report_sxw (
    'report.account_tweaks.invoice',
    'account.invoice',
    'addons/account_tweaks/report/account_print_invoice.rml',
    parser=account_invoice,
)

