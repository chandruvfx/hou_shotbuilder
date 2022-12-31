#
#
# A BFX Publisher module need to collect the abc data again with
# all new bassets published. This is a validation widget code run first
# to Collect all shot datas with the new published basset
# Works with three steps. Validation module collect all the shot data
# Section Module leave the choice the user to select the new basset
# Process module to find the specific basset belong to the step and
# made entry in the subnet menu entry and also create node inside it
#
#
from bfx_publisher.constant import CB_STATUS
from bfx_publisher.api import use_as_callback
from .build_init_shot import __STEP_SUBNETWORK_NAMES__
from . import collect_shot_datas
from ast import literal_eval
from copy import deepcopy
from BQt import QtWidgets
import hou

__module_properties__ = {
    'label': 'Click to \'Next\' Collect New Basset',
    'description': "Collect New Published Bassets",
    'callback_options_shown': True,
}

@use_as_callback
def check(tool_context, logger):

    '''
    Call Back to call the original shot data collection protocol
    obtain necessary datas.

    :param tool_context: Holds the information of passing data
    :param logger: User information logger
    :return: Status of Fail or success
    '''

    resolve_new_dict = resolve_dict()
    new_extension_dict = resolve_new_dict[0]
    new_bassets = resolve_new_dict[1]
    new_extension_list = resolve_new_dict[2]
    new_linked_assets = resolve_new_dict[3]
    new_asset_instances = resolve_new_dict[4]

    if new_bassets:
        logger.info('Shot New Bassets Collected !!!')
        tool_context['new_extension_data'] = new_extension_dict, \
                                             new_bassets, \
                                             new_extension_list, \
                                             new_linked_assets, \
                                             new_asset_instances
        return CB_STATUS.OK
    else:
        logger.info('All Latest Basset\'s Exist in Scene. NIL To Show !!!')
        return CB_STATUS.FAILED


def collect_batom_data():

    """
    Recall the shot collection module to get all the shot related
    generated datas
    """
    generate_data_dict = collect_shot_datas.GenerateExtensionDict()
    return generate_data_dict.generate_ext_data()


def resolve_dict():

    """
    Master function collects all the registered dictionary exist in the shotbuilder.
    Secondly call the data collection module to collect all the shot datas with new
    basset collected. Find the difference between old and new nested dict and regenerate
    the new dict based upon the new basset found.
    """

    calc_new_basset = {}
    nosteplist = []
    steplist =[]
    camera_dict = {}
    camera = []
    all_names = []
    asset_dependent_names = []

    def compare_dicts(dict1, dict2, linked_bassets, get_new_asset_instances):

        """
        Make new nested dict by comparing old and new dict, create the list
        of nested dict information founded for the new basset.

        Example of mock produced new basset dictionary
        {
            "lay": [
                {
                    "anim": {
                        "layout": {
                            "ple_test_6": {
                                "Low": {
                                    "model": "show/DBY/shot/pletest/pletest_0010/lay/publish/layout/v010/ple_test_6/ple_test_6_Low_GEO.abc"
                                }
                            }
                        }
                    }
                },
                {
                    "geo": {
                        "layout": {
                            "locators": "show/DBY/shot/pletest/pletest_0010/lay/publish/layout/v003/tracker.abc"
                        }
                    }
                }
            ],
            "ani": [
                {
                    "anim": {
                        "master": {
                            "ple_test_3": {
                                "High": {
                                    "model": "show/DBY/shot/pletest/pletest_0010/ani/publish/master/v007/ple_test_3/ple_test_3_High_GEO.abc"
                                },
                                "Low": {
                                    "model": "show/DBY/shot/pletest/pletest_0010/ani/publish/master/v007/ple_test3/ple_test_3_Low_GEO.abc"
                                },
                                "Mid": {
                                    "model": "show/DBY/shot/pletest/pletest_0010/ani/publish/master/v007/ple_test_3/ple_test_3_Mid_GEO.abc"
                                }
                            }
                        }
                    }
                }
            ]
        }
        :param dict1: old dict stored from the shotbuilder
        :param dict2: new dict calculated from data base call
        :param linked_bassets: basset names of the shot collected
        :param get_new_asset_instances: asset instance found for the shot
        """

        no_step = {}
        dict1 = deepcopy(dict1)
        dict2 = deepcopy(dict2)
        if not (isinstance(dict1, str) or isinstance(dict2, str)):
            keys1 = set(dict1.keys())
            keys2 = set(dict2.keys())
            for key in keys1 & keys2:
                # all key names of the nested dictionary collected in to the
                # list datastructure
                all_names.append(key)

                # camera name should need added infront if any camera
                # found out. It is easier to segregate in post node
                # creation. which used to identify which node need to
                # create, whether alembic node or alembic archieve.
                # If 'camera' literal found then create the alembic archieve
                if 'camera' == key:
                    def parse_camera(cam_dict):
                        if isinstance(cam_dict, dict):
                            camkeys = cam_dict.keys()
                            for camkey in camkeys:
                                camera.append(camkey)
                                parse_camera(cam_dict[camkey])
                    parse_camera(dict2[key])

                if key in __STEP_SUBNETWORK_NAMES__.keys():
                    global step
                    step = key
                compare_dicts(dict1[key], dict2[key], linked_bassets, get_new_asset_instances)

            for key in keys2 - keys1:
                # If key name found in the asset instance list put it as key in the
                # New key farming dictionary
                for names in get_new_asset_instances:
                    if names in all_names:
                        index_of_name = all_names.index(names)
                        asset_dependent_names = all_names[:index_of_name]

                if key in __STEP_SUBNETWORK_NAMES__.keys():
                    steplist.append(dict2[key])
                    calc_new_basset[key] = steplist
                    pass
                else:
                    if key in get_new_asset_instances:
                        outdict = {}
                        curdict = outdict
                        asset_dependent_names.append(key)

                        # asset_dependent_names collect all the names while parsing the nested dict
                        # Example:
                        # [u'lay', u'anim', u'layout', 'ple_test4', 'model', 'ple_test3', 'model']
                        # as 'lay', 'anim', 'layout' should need to added as keywhile making dictionary for
                        # new basset. Check any element starts with the founded linked asset name.
                        # ex: ['ple_test']. if the elemt contains the name then we strip out the list
                        # from that index. Resulting list wil be [u'lay', u'anim', u'layout']
                        for linked_basset in linked_bassets:
                            first_occur_basset_name = [basset
                                                       for basset in asset_dependent_names
                                                       if linked_basset in basset][0]
                            first_occurance_basset_index = asset_dependent_names.index(first_occur_basset_name)
                            filtered_asset_dependent_names = asset_dependent_names[:first_occurance_basset_index]
                        counter = 0
                        for asset_ancestor_name in filtered_asset_dependent_names:

                            # A nested dict produced {'lay':{ 'anim':{ 'layout' : {}}}}
                            #
                            # The basset dict is
                            # {'ple_test_6': {'Low': {'model':
                            # 'show/DBY/shot/pletest/pletest_0010/lay/publish/layout/v010/ple_test_6/ple_test_6_Low_GEO.abc'}}}}}]}
                            # To append the dict in 'layout': {}, a counter intiated
                            # If the counter is equal to the number of element found int filtered_asset_dependent_names
                            # then add the basset dict into the last found entry dict
                            #
                            # {'lay': [{'anim': {'layout': {'ple_test_6': {'Low':
                            # {'model': 'show/DBY/shot/pletest/pletest_0010/lay/publish/layout/v010/ple_test_6/ple_
                            # test_6_Low_GEO.abc'}}}}}]}
                            curdict[asset_ancestor_name] = {}
                            curdict = curdict[asset_ancestor_name]
                            counter = counter + 1
                            if counter == len(filtered_asset_dependent_names):
                                curdict[key] = deepcopy(dict2[key])
                        nosteplist.append(outdict[step])
                        calc_new_basset[step] = nosteplist
                    else:
                        no_step[key] = dict2[key]
                        if key in camera:
                            temp = {}
                            temp[camera[0]] = no_step
                            camera_dict['camera'] = temp
                            nosteplist.append(camera_dict)
                        else:
                            nosteplist.append(no_step)
                        calc_new_basset[step] = nosteplist

    # Once function call below part executed
    # Already registered dictionary by the shotbuilder is parsed
    extension_dict = {}
    for children in hou.node('/obj').children():
        if 'otl_name' in children.userDataDict():
            extension_dict = literal_eval(children.userDataDict()['basset_dict'])

    # Data collection module recalled
    ext_data = collect_batom_data()
    calc_new_extension_dict = deepcopy(ext_data[0])
    calc_new_extension_list = ext_data[1]
    calc_new_linked_assets = ext_data[2]
    calc_new_asset_instances = ext_data[3]

    # Compare new collected nested dict with the old dict to find the new basset
    compare_dicts(extension_dict, calc_new_extension_dict, calc_new_linked_assets, calc_new_asset_instances)
    return calc_new_extension_dict, calc_new_basset, calc_new_extension_list, calc_new_linked_assets, calc_new_asset_instances

