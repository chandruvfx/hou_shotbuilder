# -*- coding: utf-8 -*-
# section Widget Module
from BQt import QtWidgets
from .build_init_shot import __STEP_SUBNETWORK_NAMES__
from copy import deepcopy
from bfx_publisher.api import PublisherSectionWidget
from bfx_publisher.constant import SC_STATUS

__module_properties__ = {

    'label': "Select Bassets To Update in ShotBuilder Context",
    'description': "This is an example of a custom section"
}


class SectionWidget(PublisherSectionWidget, QtWidgets.QWidget):

    '''
    Section Widget with a tree widget Qt loads all the new basset
    received from the validation module and register necessary entries
    in the shotbuilder HDA
    '''

    def __init__(self, tool_context, logger):
        super(SectionWidget, self).__init__(tool_context)

        self.user_selected_basset_name_list = []
        self.temp_user_selected_raw_basset_list = []
        self.user_selected_raw_basset_list = []
        self.create_nodes_in_subnet_list = []

        self.orig_basset_solve_names = []
        self.orig_basset_name_dict = {}
        self.treewidget_items = []

        self.logger = logger

        # Operations performed in before the 'Next'
        self.before_shown.connect(self.generate_user_selected_basset_datas)

        # Operation performe after press 'Next'
        self.run.connect(self.fetch_user_selected_basset_datas)

    def generate_user_selected_basset_datas(self):

        """
        Create a Qt tree widget and add the new founded basset items
        as tree items. Left to user choice to select the basset to load
        inside shotbuilder
        :return:
        """

        extension_dict = self.tool_context['new_extension_data'][0]
        new_bassets = self.tool_context['new_extension_data'][1]
        new_extension_list = self.tool_context['new_extension_data'][2]
        new_linked_assets = self.tool_context['new_extension_data'][3]
        new_asset_instances = self.tool_context['new_extension_data'][4]

        self.extension_dict = extension_dict
        self.new_basset = new_bassets
        self.new_extension_list = new_extension_list
        self.new_linked_assets = new_linked_assets
        self.new_asset_instances = new_asset_instances

        form_layout = QtWidgets.QFormLayout()
        show_basset_names = self.get_basset_names()
        self.treewidget = QtWidgets.QTreeWidget()
        self.treewidget.setColumnCount(1)
        self.treewidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.treewidget.setHeaderLabels(['New Basset List'])
        for basset_name in show_basset_names:
            treeitem = QtWidgets.QTreeWidgetItem([basset_name])
            self.treewidget.addTopLevelItem(treeitem)
        self.treewidget.itemSelectionChanged.connect(self.gettext)
        form_layout.addRow(self.treewidget)
        self.setLayout(form_layout)

        for ext in self.new_basset.keys():
            for basset in self.new_basset[ext]:
                self.orig_basset_solve_names.append(basset.keys()[0])

        # produce {'lay/locators': 'geo', 'lay/ple_test_6': 'anim', 'ani/ple_test_3': 'anim'}
        # Keys are show in the user treewidget. once the select the value are the
        # keys of the nested dict of the particular basset. bassed upon the selection the
        # nested dict to send to solver module to create data inside shot builder
        self.orig_basset_name_dict = dict(zip(show_basset_names, self.orig_basset_solve_names))

    def get_basset_names(self):

        """
        Fill the list with new founded basset names. this list shown in to the
        tree widget items
        example: ['lay/locators', 'lay/ple_test_6', 'ani/ple_test_3']
        :return: list with new basset names
        """

        treewidget_basset_names = []

        def solve_to_get_basset_names(name_basset_dict):

            if isinstance(name_basset_dict, dict):
                basset_keys = name_basset_dict.keys()
                for resolve_basset_key in basset_keys:
                    if resolve_basset_key in __STEP_SUBNETWORK_NAMES__.keys():
                        global m_step
                        m_step = resolve_basset_key
                    if resolve_basset_key in self.new_asset_instances:
                        basset_name = m_step + '/' + resolve_basset_key
                        treewidget_basset_names.append(basset_name)
                        break
                    else:
                        for basset in name_basset_dict.values():
                            if isinstance(basset, str):
                                treewidget_basset_names.append(m_step + '/' + name_basset_dict.keys()[0])
                    if isinstance(name_basset_dict[resolve_basset_key], list):
                        for sub_basset_keys in name_basset_dict[resolve_basset_key]:
                            solve_to_get_basset_names(sub_basset_keys)
                    else:
                        solve_to_get_basset_names(name_basset_dict[resolve_basset_key])

        solve_to_get_basset_names(self.new_basset)
        filtered_treewidget_basset_names = set()
        res_tree_items = [item for item in treewidget_basset_names
                          if not (tuple(item) in filtered_treewidget_basset_names
                                  or filtered_treewidget_basset_names.add(tuple(item)))
                          ]
        return res_tree_items


    def gettext(self):

        """QtreeWidget user selection basset names parser"""

        getitems = self.treewidget.selectedItems()
        items = [item.text(0) for item in getitems]
        self.treewidget_items = items
        self.user_selected_basset_name_list = [self.orig_basset_name_dict[item] for item in items]

    def solve_user_selcted_basset(self):

        default_lod_precedence = {'Low': 0, 'Mid': 1, 'High': 2}
        self.temp_user_selected_raw_basset_list[:] = []

        def filter_dict_from_usr_selected_basset(new_bassets):

            def sub_recurcive_filter():
                for newbasset in new_bassets:
                    basset_keys = newbasset.keys()
                    for basset_key in basset_keys:
                        if basset_key in self.user_selected_basset_name_list:
                            for userselbasset in self.treewidget_items:
                                new_basset_step_search = new_basset_step + '/'
                                if new_basset_step_search in userselbasset:
                                    global same_basset_key
                                    same_basset_key = basset_key
                                    self.temp_user_selected_raw_basset_list.append(
                                        deepcopy({new_basset_step: newbasset}))
                                else:
                                    if basset_key not in newbasset:
                                        self.temp_user_selected_raw_basset_list.append(
                                            deepcopy({new_basset_step: newbasset}))

                        filter_dict_from_usr_selected_basset(newbasset[basset_key])

            if not isinstance(new_bassets, str):
                if isinstance(new_bassets, list):
                    sub_recurcive_filter()
                else:
                    new_basset_keys = new_bassets.keys()
                    for new_basset_key in new_basset_keys:
                        if new_basset_key in __STEP_SUBNETWORK_NAMES__.keys():
                            global new_basset_step
                            new_basset_step = new_basset_key
                        filter_dict_from_usr_selected_basset(new_bassets[new_basset_key])

        filter_dict_from_usr_selected_basset(self.new_basset)

        filtered_create_node_list = []
        for newbasset in self.temp_user_selected_raw_basset_list:
            if newbasset not in filtered_create_node_list:
                filtered_create_node_list.append(newbasset)
        self.user_selected_raw_basset_list = filtered_create_node_list
        self.create_nodes_in_subnet_list = deepcopy(self.user_selected_raw_basset_list)

        def remove_higher_lods(usr_sel_basset_list):

            def rec_remove_higher_lods(usr_sel_basset_dict):
                if isinstance(usr_sel_basset_dict, dict):
                    usr_sel_basset_dict_keys = usr_sel_basset_dict.keys()
                    for usr_sel_basset_key in usr_sel_basset_dict_keys:
                        if 'Low' in usr_sel_basset_dict[usr_sel_basset_key] or \
                                'Mid' in usr_sel_basset_dict[usr_sel_basset_key] or \
                                'High' in usr_sel_basset_dict[usr_sel_basset_key]:

                            if not isinstance(usr_sel_basset_dict[usr_sel_basset_key], str):
                                index = min(
                                    [default_lod_precedence[key]
                                     for key in usr_sel_basset_dict[usr_sel_basset_key].keys()]
                                )
                                if index == 0:
                                    lod = 'Low'
                                if index == 1:
                                    lod = 'Mid'
                                if index == 2:
                                    lod = 'High'
                                for usr_sel_basset_lod in usr_sel_basset_dict[usr_sel_basset_key].keys():
                                    if usr_sel_basset_lod != lod:
                                        del usr_sel_basset_dict[usr_sel_basset_key][usr_sel_basset_lod]

                        remove_higher_lods(usr_sel_basset_dict[usr_sel_basset_key])

            if isinstance(usr_sel_basset_list, list):
                for usr_sel_basset in usr_sel_basset_list:
                    rec_remove_higher_lods(usr_sel_basset)
            else:
                rec_remove_higher_lods(usr_sel_basset_list)
        remove_higher_lods(self.user_selected_raw_basset_list)
        if self.treewidget_items:
            self.logger.info("New Bassets Selected From User\n%s" % '\n'.join(self.treewidget_items))
        else:
            self.logger.error("No Bassets Selected")

    def fetch_user_selected_basset_datas(self):

        """
        Fetch generated new datas to process module
        """

        self.solve_user_selcted_basset()
        if self.treewidget_items:
            self.tool_context['new_extension_data'] = self.user_selected_basset_name_list, \
                                                 self.user_selected_raw_basset_list, \
                                                 self.create_nodes_in_subnet_list, \
                                                 self.new_extension_list, \
                                                 self.new_asset_instances, \
                                                 self.treewidget_items, \
                                                 self.new_linked_assets
            self.logger.info("Fetching Selected Bassets To Process\n%s" % '\n'.join(self.treewidget_items))
            self.status = SC_STATUS.OK
        else:
            self.logger.error("No Basset To Fetch")
            self.status = SC_STATUS.HAS_ERROR