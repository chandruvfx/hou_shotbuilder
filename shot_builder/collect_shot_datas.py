#
# A module Recursively travel through the batom and sub-batom of all the usable version
# of all steps from a given task context and collects the user specified extension files
# of the shot.

from bfx.api import (TaskContext,
                     PLE_Entity,
                     create_burl,
                     BURL,
                     create_kuaidi_package)

from bfx.env.constants import LocationInfo
from bfx.api import PLE_Entity as Entity
from os.path import (splitext,
                     exists)
import itertools
import fnmatch
import json
import os


class GenerateExtensionDict:

    """
    A master class to recursively traverse batom and sub-batom and collects
    user specified extension file of the shot from the given current task
    context. Returns few datas
    1. nested list having flattend infomation of all batom,
    2. a nested dictionary constructed from the nested list, and
    3. basset names linked to the shots.
    4. basset instance names of the shots

    HOW IT WORKS:
    ------------
    This class do several tasks. It collects all the related bassets instance
    names. Checks, if all usable versions in all steps is physically exist in
    the isilon. If not it submit kuaidi jobs of the missing version path.
    Else, It recursively solve all the batom and build the nested dict for
    the given extension(.abc)

    Example:
    ________

    generate_data_dict = collect_shot_datas.Generate_Extension_Dict()
    return self.generate_data_dict.generate_ext_data()

    """

    def __init__(self, debug=False):

        self.task_context = TaskContext.from_env()
        self.debug = debug
        self.asset_def = []
        self.extension_list = []
        self.extention_dict = {}
        self.related_assets = set()
        self.current_asset_instance = ''
        self.asset_instances = set()

        # Get preset to Extract basset import rule dict
        self.presets = \
            self.task_context.get_presets(context={"app": "houdini", "tool": "efx_builder"},
                                          refresh=True)
        self.import_rule = ''

    def basset_import_rule(self):

        """Search only those specified basset rule in the found version,

        Extract a basset import rule dict from efx_builder.presets

        A Dict Example returned in self.import_rule
        [
            {
                "filter": [ "and",
                    [ "exact", "app", "houdini" ],
                    [ "exact", "tool", "efx_builder" ]
                 ],
                "data": {
                    "step_precedence" : "sfn>ani>lay>mmd",
                    "bassets_import_rule" :[
                        {
                           "step_rule": {
                                "ani": ["*master*"],
                                "lay": ["*layout*"],
                                "mmd": ["*tracking*"],
                                "sfn": ["*master*"]
                            }
                        }
                    ]
                }
            }
        ]
        :return: import_rule or warning message
        """

        if 'bassets_import_rule' in self.presets:
            self.import_rule = self.presets['bassets_import_rule'][0]['step_rule']

            return self.import_rule
        else:
            try:
                import hou
                hou.ui.displayMessage("Configure efx_builder presets!!",
                                      title='Shot Builder')
                exit()
            except ImportError:
                pass

    def loc_abc_import_mode(self):

        """
        Method determines location basset created with alembic node or
        ani import hda
        :return: integer. 0 abc node created 1 ani import hda created
        """

        if 'loc_abc_import_mode' in self.presets:
            return self.presets['loc_abc_import_mode']
        else:
            return 0

    def collect_related_assets(self, atom_object_parts,
                               batom_file, atom_object,
                               names, basset_names):
        """
            Collect related asset instances using asset names found
            out in the rig_def example: Korg_1, korgclub_1
        """
        def find_asset_name(asset_burl_path):

            asset_name = BURL(asset_burl_path).entity.parent.name
            self.related_assets.add(asset_name)

        def resolve_sub_batom(battom_path):

            atom_object_part = atom_object.part_to_sub_atom(
                        battom_path,
                        battom_path.rsplit(os.sep, 1)[0]
            )
            for names in atom_object_part.atom.get_names():
                if names == 'rig_def':
                    find_asset_name(atom_object_part.atom.get_part(names))

                self.collect_related_assets(
                            atom_object_part.atom.get_part(names),
                            battom_path,
                            atom_object,
                            names,
                            basset_names
                )

        try:

            if not hasattr(atom_object_parts, 'get_names'):
                burl_atom_object_parts = BURL(atom_object_parts)
                if burl_atom_object_parts.is_valid:
                    if burl_atom_object_parts.real_path.endswith('.batom'):
                        resolve_sub_batom(burl_atom_object_parts.real_path)

                if atom_object_parts.endswith('.batom'):
                    batom_path = atom_object.part_to_path(
                                atom_object.get_part(names),
                                batom_file.rsplit(os.sep, 1)[0]
                    )
                    resolve_sub_batom(batom_path)

            for names in atom_object_parts.get_names():
                if names == 'rig_def':
                    find_asset_name(atom_object_parts.get_part(names))
                part_data = atom_object_parts.get_part(names)

                if str(part_data).endswith('.batom'):
                    resolve_sub_batom(part_data)

                else:
                    if hasattr(part_data, 'get_names'):
                        self.collect_related_assets(
                                        part_data,
                                        batom_file,
                                        atom_object,
                                        names,
                                        basset_names
                        )
        except:
            pass

    def generic_extension_collector(self, atom_object_parts, batom_file,
                                    atom_object, names, basset_names,
                                    extension, asset_name_parts=None,
                                    version_asset=None):

        """ Method recursively solves the batom and retrive extension data
        Create a nested dict with asset name with ext path information
        Build a nested extension list.
        """
    
        if asset_name_parts not in ['rig_data','rig_def']:
            self.asset_def.append(str(asset_name_parts))
        null_str_index=0
        if '\x00' in self.asset_def:
            null_str_index = max(null for null,null_index in enumerate(self.asset_def) if null_index=='\x00')

        def resolve_sub_batom(battom_path):

            """Hook resolve sub-battom if any battom found out in primary case

            Resolve sub-bottom and found out result again passed to the
            master funtion call to resolve battom parts.

            :param battom_path:.batom file path
            """
    
            atom_object_part = atom_object.part_to_sub_atom(battom_path, battom_path.rsplit(os.sep, 1)[0])
            for names in atom_object_part.atom.get_names():

                self.generic_extension_collector(
                            atom_object_part.atom.get_part(names),
                            battom_path, atom_object,
                            names, basset_names,
                            extension, asset_name_parts,
                            version_asset
                )
    
        def collect_extentions(part_data):

            """Master Hook which construct the nested list with the basset info, lods
            and extension info.

            :param part_data: battom object
            :return:
            """
    
            path = str(atom_object.part_to_path(part_data, batom_file.rsplit(os.sep, 1)[0]))
            burl = create_burl(path)
            asset_def_list_with_none = self.asset_def[null_str_index+1:]
            none_count = asset_def_list_with_none.count('None')
            asset_def_list = asset_def_list_with_none[none_count:]

            if 'None' in asset_def_list:
                asset_def_list.remove('None')
            upstream_asset = list(set(filter(lambda x:x!='\x00', asset_def_list)))
            sorted_asset_list = sorted(upstream_asset, key=lambda x: asset_def_list.index(x))

            if len(self.related_assets) != 0:
                for asset in sorted_asset_list:
                    for related_assets in self.related_assets:
                        if related_assets in asset:
                            self.current_asset_instance = asset
                            self.asset_instances.add(asset)
            global lod_mode
            if self.current_asset_instance in sorted_asset_list and 'High' in sorted_asset_list:
                lod_mode = 1
            elif self.current_asset_instance in sorted_asset_list and 'Mid' in sorted_asset_list:
                lod_mode = 1
            elif self.current_asset_instance in sorted_asset_list and 'Low' in sorted_asset_list:
                lod_mode = 1

            if sorted_asset_list != [] and names != extension:
                if sorted_asset_list[0] != sorted_asset_list[-1]:
                    if sorted_asset_list[0] not in list(self.asset_instances):
                        sorted_asset_list.remove(sorted_asset_list[0])
                    self.extension_list.append(
                        [burl.entity.name, version_asset, basset_names, sorted_asset_list[0], sorted_asset_list[-1],
                         names, path]
                    )
                else:
                    if basset_names not in self.asset_instances:
                        if lod_mode == 1:
                            if 'Low' in sorted_asset_list:
                                sorted_asset_list.insert(0, self.current_asset_instance)
                            if 'Mid' in sorted_asset_list:
                                sorted_asset_list.insert(0, self.current_asset_instance)

                    if sorted_asset_list[0] != sorted_asset_list[-1]:
                        self.extension_list.append(
                            [burl.entity.name, version_asset, basset_names, sorted_asset_list[0], sorted_asset_list[-1], names, path]
                        )

                    else:
                        self.extension_list.append(
                            [burl.entity.name, version_asset, basset_names, sorted_asset_list[0], names, path]
                        )

            elif sorted_asset_list != [] and names == extension:
                self.extension_list.append(
                    [burl.entity.name, version_asset, basset_names, sorted_asset_list[0], path]
                )

            elif sorted_asset_list == [] and names == extension:
                self.extension_list.append(
                    [burl.entity.name, version_asset, basset_names, path]
                )

            else:
                self.extension_list.append(
                    [burl.entity.name, version_asset, basset_names, names, path]
                )

            if self.debug:
                print(burl.entity.name, '->', \
                      basset_names, '->', \
                      sorted_asset_list, \
                      '->', names, \
                      '->', path)

        try:
    
            if not hasattr(atom_object_parts, 'get_names'):
                burl_atom_object_parts = BURL(atom_object_parts)
                if burl_atom_object_parts.is_valid:
                    if burl_atom_object_parts.real_path.endswith('.batom'):
                        resolve_sub_batom(burl_atom_object_parts.real_path)

                    elif burl_atom_object_parts.real_path.endswith('.' + extension):
                        collect_extentions(atom_object_parts)
                        self.asset_def.append('\x00')
    
                if atom_object_parts.endswith('.' + extension):
                    collect_extentions(atom_object_parts)
                    self.asset_def.append('\x00')
    
                if atom_object_parts.endswith('.batom'):
                    batom_path = atom_object.part_to_path(atom_object.get_part(names), batom_file.rsplit(os.sep, 1)[0])
                    resolve_sub_batom(batom_path)
    
            for names in atom_object_parts.get_names():
                asset_name_parts = names
                part_data = atom_object_parts.get_part(names)
    
                if str(part_data).endswith('.batom'):
                    resolve_sub_batom(part_data)
    
                else:
                    if isinstance(part_data, unicode):
                        burl_part_data = BURL(part_data)
                        if str(part_data).endswith('.' + extension):
                            collect_extentions(part_data)
                            self.asset_def.append('\x00')
    
                        elif burl_part_data.is_valid:
                            if burl_part_data.real_path.endswith('.' + extension):
                                collect_extentions(part_data)
                                self.asset_def.append('\x00')
                                
                    if hasattr(part_data, 'get_names'):
                        asset_name_parts = names
                        self.generic_extension_collector(
                                    part_data, batom_file,
                                    atom_object, names,
                                    basset_names, extension,
                                    asset_name_parts,version_asset
                        )
        except:
            pass

    def generate_ext_data(self):

        """Master method to create nested dictionary from the data obtained
        from generic extention collector

        Collects relates asset instance of the shot . check the version
        files are exist physically in the isilon. unavailable versions
        submitted as kuaidi job and would not allow the shotbuilder proceed
        further. If all basset version found then it resolves and
        returns nested dict

        :return: extention_dict - nested dict contain all information
                 of basset usable version names and extension path
                 extension_list - list which used to build dict
                 related_assets - related asset info collected from
                                  rig_def
                 asset_instances - asset instance found out from
                                   related assets
        """
        self.__collect_related_assets()
        status_list, sync_files, job_ids = self.__check_files_exist()
        if all(status_list):
            self.__collect_basset_dict()

            for extensions_list in self.extension_list:
                temp_ext_dict = self.extention_dict

                for extentions in extensions_list:
                    extract_ext = str([i for i in extensions_list if i.endswith('.abc')][0])
                    extention_parent_label = \
                    [
                        extensions_list[
                            extensions_list.index(i) - 1
                        ]
                        for i in extensions_list if i.endswith('.abc')
                    ][-1]
                    if extentions not in temp_ext_dict:
                        if extentions.endswith('.abc'):
                            continue

                        elif extentions == extention_parent_label:
                            temp_ext_dict[extentions] = extract_ext[1:]

                        elif extentions != extention_parent_label:
                            temp_ext_dict[extentions] = {}

                    temp_ext_dict = temp_ext_dict[extentions]

            return self.extention_dict, \
                   self.extension_list, \
                   list(self.related_assets), \
                   list(self.asset_instances)
        else:
            job_id_dict = {}
            for sync_file, job_id in zip(sync_files, job_ids):
                job_id_dict[job_id] = sync_file

            return {'sync_files':job_id_dict}

    def __collect_related_assets(self):

        """
        Extract basset regex rule specified in efx_builder preset.
        Iterate through all the specified bassets of each step of the
        current task context and get the related asset names from rig_def
        """

        import_rule = self.basset_import_rule()

        for step in self.task_context.entity.parent.children:
            for basset in step.assets:
                import_basset_list = list(set(list(itertools.chain(*import_rule.values()))))
                check_basset_availability = \
                    [True for
                     import_basset in import_basset_list
                     if fnmatch.fnmatch(basset.name, import_basset)
                     ]

                if check_basset_availability:
                    if step.name in import_rule.keys() and check_basset_availability[0]:
                        try:
                            version = basset.get_usable_version()
                            batom_file = version.get_exporter().get_files(role='atom')[0]
                            atom_object = version.get_exporter().get_atom_object()

                            for names in atom_object.get_names():
                                self.collect_related_assets(
                                        atom_object.get_part(names),
                                        batom_file,
                                        atom_object,
                                        names,
                                        basset.name
                                )

                        except:
                            pass

    def submit_kuaidi_package(self,
                              exporter_file,
                              src_location,
                              dst_location):

        submitted_job_id = create_kuaidi_package(src_root=exporter_file,
                                                 src_location=src_location,
                                                 dst_root=exporter_file,
                                                 dst_location=dst_location,
                                                 priority=3,
                                                 parent=None,
                                                 label="")
        return submitted_job_id

    def __check_files_exist(self):

        """
        Check whether the collected version is physically exist in the isilon
        if not it submit kuaidi job. The master function call stop proceed
        further to build the shot
        :return: kuaidi job id
        """

        import_rule = self.basset_import_rule()

        file_status_list = []
        sync_lib = []
        job_ids = []
        dependency_version_list = []
        dst_location = LocationInfo.code
        for step in self.task_context.entity.parent.children:
            try:
                for basset in step.assets:
                    import_basset_list = list(set(list(itertools.chain(*import_rule.values()))))
                    check_basset_availability = \
                        [True
                         for import_basset in import_basset_list
                         if fnmatch.fnmatch(basset.name, import_basset)
                         ]

                    if check_basset_availability:
                        if step.name in import_rule.keys() and check_basset_availability[0]:
                            version = basset.get_usable_version()
                            for x in version.sources:
                                dependency_version_list.append(x.default_burl.real_path)

                            exporter_files = version.get_exporter().get_files()
                            src_location = version.created_from

                            if filter(lambda x: x.endswith('.abc'), exporter_files) or \
                                    filter(lambda x: x.endswith('.batom'), exporter_files):
                                version_exporter = version.get_exporter()

                                for exporter_file in exporter_files:
                                    for related_asset in list(self.related_assets):
                                        _, ext = splitext(exporter_file)
                                        if ext == '' and related_asset in exporter_file:
                                            stat_ver = exists(exporter_file)
                                            file_status_list.append(stat_ver)
                                            if not stat_ver:
                                                sync_lib.append(exporter_file)
                                                job_id = self.submit_kuaidi_package(exporter_file, src_location, dst_location)
                                                job_ids.append(job_id)

                                exp_path = version_exporter.basset_url.real_path
                                stat_export = exists(exp_path)
                                file_status_list.append(stat_export)

                                if not stat_export:
                                    sync_lib.append(exp_path)
                                    job_id = self.submit_kuaidi_package(exp_path, src_location, dst_location)
                                    job_ids.append(job_id)

                        if dependency_version_list:
                            for dependencies in dependency_version_list:
                                sync_lib.append(dependencies)
                                dependent_job_id = self.submit_kuaidi_package(dependencies, src_location, dst_location)
                                job_ids.append(dependent_job_id)
            except:
                pass
        return file_status_list, sync_lib, [id for job_id in job_ids for id in job_id]

    def __collect_basset_dict(self):

        """
        A primary method hook call the extension collector function to resolve
        batom files to collect all the necessary data to build the shot
        """

        import_rule = self.basset_import_rule()

        for step in self.task_context.entity.parent.children:
            for basset in step.assets:
                import_basset_list = list(set(list(itertools.chain(*import_rule.values()))))
                check_basset_availability = \
                    [True
                     for import_basset in import_basset_list
                     if fnmatch.fnmatch(basset.name, import_basset)
                     ]

                if check_basset_availability:
                    if step.name in import_rule.keys() and check_basset_availability[0]:
                        try:
                            version = basset.get_usable_version()
                            batom_file = version.get_exporter().get_files(role='atom')[0]
                            atom_object = version.get_exporter().get_atom_object()

                            for names in atom_object.get_names():
                                version_asset = names

                                self.generic_extension_collector(
                                            atom_object.get_part(names),
                                            batom_file,
                                            atom_object,
                                            names,
                                            basset.name,
                                            'abc',
                                            asset_name_parts=None, version_asset=version_asset
                                )
                        except:
                            pass


if __name__ == '__main__':
    obj = GenerateExtensionDict(debug=True)
    print(json.dumps(obj.generate_ext_data()[0], indent=4))

