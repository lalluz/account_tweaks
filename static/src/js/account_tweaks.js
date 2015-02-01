openerp.account_tweaks = function (instance) {

    instance.web.TreeView.include ({
        load_tree: function (fields_view) {
            this._super.apply (this, arguments);

            if (fields_view.name == 'account.tax.code.tree') {
                var period_id = this.dataset.context.period_id;
                var state = this.dataset.context.state;

                instance.account_tweaks.fetch_liquidazione_iva (period_id, state);
            }
        }
    });

    instance.account_tweaks.fetch_liquidazione_iva = function (period_id, state) {
        var params = {
            'period_id': period_id,
            'state': state
        };

        instance.session.rpc ('/liquidazione-iva/json_url', params).done (function (result) {
            var div = jQuery(".oe_view_manager_body");

            div.append (result);

        }).fail (function (result) {
            console.log ("ERROR: " + result.message);
        });

        return false;
    };

    instance.web.account.ReconciliationListView.include ({
        load_list: function () {
            var self = this;
            var tmp = this._super.apply (this, arguments);
            if (this.partners) {
                this.$(".oe_account_recon_select").change (function () {
                    self.current_partner = (((this.selectedIndex) % self.partners.length) + self.partners.length) % self.partners.length;
                    self.search_by_partner ();
                });
            }
            return tmp;
        }
    });

    instance.account_tweaks.CategoryReconciliationListView = instance.web.account.ReconciliationListView.extend ({
        list_to_reconcile: null,

        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(instance.web.ListView.prototype.do_search, this);
            var mod = new instance.web.Model("account.move.line", context, domain);
            return mod.call(self.list_to_reconcile, []).then(function(result) {
                var current = self.current_partner !== null ? self.partners[self.current_partner][0] : null;
                self.partners = result;
                var index = _.find(_.range(self.partners.length), function(el) {
                    if (current === self.partners[el][0])
                        return true;
                });
                if (index !== undefined)
                    self.current_partner = index;
                else
                    self.current_partner = self.partners.length == 0 ? null : 0;
                self.search_by_partner();
            });
        }
    });

    instance.account_tweaks.SupplierReconciliationListView = instance.account_tweaks.CategoryReconciliationListView.extend ({
        list_to_reconcile: "list_suppliers_to_reconcile",
    });

    instance.web.views.add ('tree_account_reconciliation_supplier', 'instance.account_tweaks.SupplierReconciliationListView');

    instance.account_tweaks.CustomerReconciliationListView = instance.account_tweaks.CategoryReconciliationListView.extend ({
        list_to_reconcile: "list_customers_to_reconcile",
    });

    instance.web.views.add ('tree_account_reconciliation_customer', 'instance.account_tweaks.CustomerReconciliationListView');

    instance.web.Sidebar.include ({
        on_attachments_loaded: function (attachments) {
            var self = this;
            var attachment_obj = new instance.web.DataSet (self, 'ir.attachment');

            self._super (attachments);

            self.$el.find ('.oe_sidebar_delete_item').hide ();
            _.each (attachments, function (a) {
                attachment_obj._model.call ('can_be_deleted', [a.id]).done (function (res) {
                    if (res) {
                        self.$el.find ('.oe_sidebar_delete_item[data-id=' + a.id + ']').show ();
                    }
                });
            });
        }
    });

    instance.account_tweaks.CompanyVsPrivateCustomerInvoicesAction = instance.web.Widget.extend ({
        template: 'account_tweaks.company_vs_private_customer_invoices_template',

        get_results: function () {
            var self = this.$el;

            var url = '/company_vs_private_customer_invoices/json_url';
            var params = {
                'start': self.find ("#date_from").val(),
                'end':  self.find ("#date_to").val(),
            };

            instance.session.rpc (url, params).done (function (result) {
                var div = self.find ('#oe_account_tweaks_results');

                div.empty ()
                div.append (result);
            }).fail (function (result) {
                console.log ("ERROR: " + result.message);
            });
        },

        events: {
            "click #search-button": 'get_results',
        },

        start: function () {
            var body = this.$el.parents ('body');

            var start = this.$el.find ("#date_from");
            var end = this.$el.find ("#date_to");

            var date = new Date(), y = date.getFullYear(), m = date.getMonth();

            start[0].valueAsDate = new Date ().setFullYear (y, m, 1);
            end[0].valueAsDate = new Date ().setFullYear (y, m + 1, 0);
        },
    });

    instance.web.client_actions.add ('account_tweaks.action_company_vs_private_customer_invoices',
                                     'instance.account_tweaks.CompanyVsPrivateCustomerInvoicesAction');

};

