# -*- coding: utf-8 -*-

import base64

if __name__ == '__main__':
    import sys
    sys.path.insert (0, '/home/guido/src/openerp/server')

import openerp
import openerp.http as http
from openerp.http import request

from openerp import SUPERUSER_ID

from collections import OrderedDict


TEMPLATE = '''
<style type="text/css">
  #liquidazione-iva {
    padding: 20px 10px;
  }

  #liquidazione-iva table td:last-child {
    padding-left: 40px;
    text-align: right;
  }
</style>

<div id="liquidazione-iva">
  <h2>Liquidazione IVA</h2>
  <table>
    <tr>
      <td>IVA a debito:</td>
      <td>%(debit_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito:</td>
      <td>%(credit_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito non detraibile:</td>
      <td>%(credit_n_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito non detraibile pro rata:</td>
      <td>%(credit_prorata_vat_amount).2f</td>
    </tr>

    <tr><td>&#160;<td></tr>

    <tr>
      <td>Ricavi 74ter CEE:</td>
      <td>%(debit_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Costi 74ter CEE:</td>
      <td>%(credit_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Guadagni 74ter CEE:</td>
      <td>%(amount_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Credito di costo 74ter:</td>
      <td>%(total_previous_74ter_credit).2f</td>
    </tr>
    <tr>
      <td>IVA 74ter:</td>
      <td>%(net_vat_74ter).2f</td>
    </tr>
  </table>
</div>
'''


def _get_liquidazione_iva (registry, cr, period_id, state):
    AccountPeriod = registry.get ('account.period')

    period = AccountPeriod.browse (cr, SUPERUSER_ID, [period_id])[0]

    liquidazione = period._compute_liquidazione (None, None, {'state': state}).items ()[0][1]

    liquidazione.update (period._total_previous_74ter_credit ().items ()[0][1])

    return liquidazione


class LiquidazioneIvaController (http.Controller):

    _cp_path = '/liquidazione-iva'

    @http.route ('/liquidazione-iva/json_url', type='json')
    def json_url (self, period_id=None, state=None):
        return TEMPLATE % _get_liquidazione_iva (
            request.registry,
            request.cr,
            period_id,
            state,
        )


if __name__ == '__main__':
    from openerp.modules.registry import RegistryManager

    from openerp.netsvc import init_logger
    init_logger ()

    import pprint

    registry = RegistryManager.get (sys.argv[1], update_module=False)
    cr = registry.db.cursor ()

    AccountPeriod = registry.get ('account.period')
    period_code = '01/2014' if len (sys.argv) < 2 else sys.argv[1]
    period_id = AccountPeriod.search (cr, SUPERUSER_ID, [('code', '=', period_code)])[0]

    liquidazione_iva = _get_liquidazione_iva (registry, cr, period_id, 'all')

    print "\nLiquidazione IVA for %s\n" % period_code
    pprint.pprint (liquidazione_iva.items ())
    print ""

    cr.close ()

