#-------------------------------------------------------------------------------
# Name:        OdfEdit
# Purpose:     Application helping to edit an organ definition file (ODF) in plain text
#              The ODF can be used in the GrandOrgue application
#              Implemented with Python 3
#              Tested in Windows 10 and Ubuntu 21.10
#              It is contains 3 classes :
#                   C_ODF to manage and check the ODF data
#                   C_GUI to manage the graphical user interface
#                   CreateToolTip to display a tool tip on a GUI widget
# Author:      Eric Turpault (France, Châtellerault)
# Copyright:   open source
# Licence:     free to modify, please share the modification with the author
#
# The considered ODF syntax is :
#    [object_ID]
#    ; comment line, empty lines are ignored
#    ; object_ID can contain only alphanumeric characters
#    attribute1=value1
#    attribute2=value2
#    ; attribute can contain only alphanumeric or '_' characters
#
# The new panel format is detected if the object Panel000 is present and it contains the attribute NumberOfGUIElements
#
# Versions history :
#   v1.0 - 15 April 2022 - initial version
#   v1.1 - 16 April 2022 - minor changes to be Linux compatible, minor GUI fixes
#   v1.2 - 27 April 2022 - some GUI behavior improvements, minor improvements in the help and the objects checks
#   v1.3 - 19 May   2022 - data management improvement, change in the way to define the parent-child relations between the objects,
#                          completed some attributes values maximum check, added a tab to search a string in the whole ODF
#
#-------------------------------------------------------------------------------

MAIN_WINDOW_TITLE = "OdfEdit - v1.3"

import os
import inspect
from tkinter import *
from tkinter import filedialog as fd
from tkinter import messagebox, ttk

IDX_OBJ_NAME = 0 # index in the objects dictionnary entry list of the object name
IDX_OBJ_PAR = 1  # index in the objects dictionnary entry list of the object parents
IDX_OBJ_CHI = 2  # index in the objects dictionnary entry list of the object children
IDX_OBJ_LINE = 3 # index in the objects dictionnary entry list of the object ID line number in the ODF lines list
ENCODING_ISO_8859_1 = 'ISO-8859-1'  # one of the two supported encoding type for an ODF
ENCODING_UTF8_BOM = 'utf_8_sig'     # one of the two supported encoding type for an ODF
ALLOWED_CHARS_4_FIELDS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'  # characters allowed in a attribute name

# data types used in the attributes of the objects, used in the check object/attribute functions
ATTR_TYPE_INTEGER = 1
ATTR_TYPE_FLOAT = 2
ATTR_TYPE_BOOLEAN = 3
ATTR_TYPE_STRING = 4
ATTR_TYPE_COLOR = 5            # used in Button, Enclosure, Label, Panel
ATTR_TYPE_FONT_SIZE = 6        # used in Button, Enclosure, Label
ATTR_TYPE_PANEL_SIZE = 7       # used in Panel
ATTR_TYPE_COUPLER_TYPE = 8     # used in Coupler
ATTR_TYPE_ELEMENT_TYPE = 9     # used in Panel Element
ATTR_TYPE_TREMULANT_TYPE = 10  # used in Tremulant
ATTR_TYPE_PISTON_TYPE = 11     # used in Piston
ATTR_TYPE_DRAWSTOP_FCT = 12    # used in DrawStop
ATTR_TYPE_FILE_NAME = 13       # used in many objects for bitmap or wav files
ATTR_TYPE_OBJECT_REF = 14      # used in many objects to make a reference to another object ID
ATTR_TYPE_PIPE_WAVE = 15       # used in Rank

class C_ODF:
    #--- class to store and manage the ODF data

    odf_file_name = ""      # name of the ODF file which the data have been loaded in odf_lines_list
    odf_file_encoding = ""  # encoding type of the loaded ODF file
    odf_lines_list = []     # list containing the lines coming from the loaded ODF
    odf_objects_dict = {}   # dictionnary having as keys the objects IDs of the ODF (sorted). Each key has as value a list with the following items :
                            #   item 1 (index IDX_OBJ_NAME) : object names (string)
                            #   item 2 (index IDX_OBJ_PAR)  : object parents (list of objects ID)
                            #   item 3 (index IDX_OBJ_CHI)  : object children (list of objects ID)
                            #   item 4 (index IDX_OBJ_LINE) : number of the line in the ODF lines list where is located the object_ID of the key (integer)
                            # summarized like this : ['object_names', ['parent1_obj_ID', 'parent2_obj_ID',...], ['child1_obj_ID', 'child2_obj_ID',...], line_number]
    new_panel_format = False  # flag indicating if the odf_lines_list uses the new panel format or not
    check_files_names = ""  # flag storing the choice of the user to check or not the files names in the ODF ('' for not defined, False, True)
    check_nb_attr = 0       # number of attributes checked during the checking operation
    events_log_list = []    # list of events logs (errors or messages resulting from file operation or syntax check)

    #-------------------------------------------------------------------------------------------------
    def odf_lines_load(self, file_name):
        #--- load in odf_lines_list the content of the given ODF
        #--- returns True/False whether the file has been loaded correctly or not

        self.events_log_add(f"Loading the file '{file_name}'")

        # open the given ODF in read mode, and check its encoding format
        try:
            f = open(file_name, mode='r', encoding=ENCODING_ISO_8859_1)
        except OSError as err:
            # it has not be possible to open the file
            self.events_log_add(f"Cannot open the file. {err}")
            valid_odf_file = False
        else:
            if f.readline(3) == "ï»¿":  # UTF-8 BOM file encoding header
                # close the file
                f.close()
                # reopen the file with the proper encoding format
                f = open(file_name, mode='r', encoding=ENCODING_UTF8_BOM)
                self.odf_file_encoding = ENCODING_UTF8_BOM
            else:
                f.seek(0)  # reset the position of the cursor at the beginning of the file
                self.odf_file_encoding = ENCODING_ISO_8859_1
            # store the name of the ODF
            self.odf_file_name = file_name
            valid_odf_file = True

            # clear the lists/dict content
            self.odf_lines_list.clear()
            self.odf_objects_dict.clear()

            # load in the ODF lines list the content of the given ODF
            line_nb = 0
            attr_nb = 0
            object_ID = ''
            object_ID_list = []
            for line in f:
                if line[-1:] == '\n': line = line[:-1]  # remove the ending \n characters if any
                line = line.rstrip()  # remove the trailing whitespaces if any
                line_nb += 1  # increment the counter counting the number of loaded lines

                if self.is_line_with_object_ID(line): # line with an object ID
                    object_ID = line[1:-1] # remove the brackets in first and last characters to get the object ID

                    while object_ID in object_ID_list:
                        # there is already an object ID with the same name in the list : add _ at end of the ID until the ID is unique
                        # this is done in order to avoid duplicate IDs in the objects list, the user will have to fix it
                        self.events_log_add(f"Another occurence of the object {object_ID} is present, it has been renamed in {object_ID}_")
                        object_ID += '_'
                    line = '[' + object_ID + ']'
                    # add the object ID to the objects list
                    object_ID_list.append(object_ID)
                elif self.is_line_with_attribute(line): # line with an attribute
                    attr_nb += 1 # increment the counter counting the number of defined objects

                # add the line to the ODF lines list
                self.odf_lines_list.append(line)

            # close the ODF
            f.close()

            # update the objects dictionnary from the ODF lines list content
            self.objects_dict_update()
            # update the panel format flag from the ODF lines list content
            self.check_odf_panel_format()
            # reset the check files names flag
            self.check_files_names = ''

            self.events_log_add(f"Loading completed : {str(line_nb)} lines, {str(len(object_ID_list))} objects, {str(attr_nb)} attributes, file encoding {self.odf_file_encoding}")

        return valid_odf_file

    #-------------------------------------------------------------------------------------------------
    def odf_lines_save(self, file_name):
        #--- save odf_lines_list in the given ODF
        #--- if no file name is given, the saving is done in the already loaded ODF file
        #--- returns True/False whether the writting in file has been done correctly or not

        if len(self.odf_lines_list) == 0:
            # the ODF lines list is empty, there are no data to save
            self.events_log_add(f"None data to save in the file {file_name}")
            file_saved = False
        elif file_name == '' and self.odf_file_name == '':
            # no file name known, so no possibility to make the save operation
            file_saved = False
        else:
            # open the given ODF in write mode
            if file_name == '':
                # no given file name, make the saving in the already loaded ODF
                file_name = self.odf_file_name

            if self.odf_file_encoding == '':
                self.odf_file_encoding = ENCODING_UTF8_BOM

            # check if the file name has an extension, if not add the .organ extension
            if file_name[-6:] != '.organ':
                file_name += '.organ'

            try:
                f = open(file_name, mode='w', encoding=self.odf_file_encoding)
            except OSError as err:
                self.events_log_add(f"Cannot write in the file. {err}")
                file_saved = False
            else:
                # write odf_lines_list in the ODF, removing the consecutive empty lines, and ensuring an empty line before each object ID
                prev_line = ''
                for line in self.odf_lines_list:
                    if line[:1] == '[' and prev_line != '':
                        # object ID line without empty line before : add an empty line
                        f.write('\n')
                    if not (line == '' and prev_line == ''):
                        # not empy line following a previous empty line (to remove consecutive empty lines)
                        # write the line in the file
                        f.write(line + '\n')
                    prev_line = line
                f.close()
                file_saved = True

                # store the name of the ODF file
                self.odf_file_name = file_name

                self.events_log_add(f"Data saved in file '{file_name}' with encoding {self.odf_file_encoding}")

        return file_saved

    #-------------------------------------------------------------------------------------------------
    def odf_reset_all_data(self):
        #--- reset all the data of the class

        self.odf_file_name = ''
        self.odf_file_encoding = ENCODING_ISO_8859_1
        self.odf_lines_list.clear()
        self.odf_objects_dict.clear()
        self.events_log_clear()
        self.new_panel_format = False

    #-------------------------------------------------------------------------------------------------
    def events_log_add(self, log_string):
        #--- add the given string to the events log list

        self.events_log_list.append(log_string)

    #-------------------------------------------------------------------------------------------------
    def events_log_clear(self):
        #--- clear the events log list

        self.events_log_list.clear()

    #-------------------------------------------------------------------------------------------------
    def objects_dict_update(self):
        #--- (re)build the ODF objects dictionnary from the ODF lines list

        # parse the ODF lines list to recover all the present objects IDs
        object_ID_list = []
        for line in self.odf_lines_list:
            if self.is_line_with_object_ID(line):
                # line with an object ID : add it in the objects ID list without the surrounding brackets
                object_ID_list.append(line[1:-1])
        # sort the objects ID list
        object_ID_list.sort()

        # initialize the ODF objects dictionnary using the items of the objects ID list as the keys of the dictionnary
        self.odf_objects_dict.clear()
        for object_ID in object_ID_list:
            self.odf_objects_dict[object_ID] = ['', [], [], -1]  # set the format of each entry of the dictionnary

        object_ID = ''  # ID of the object for which we are parsing the attributes

        # parse the ODF lines list to fill the dictionnary values
        for index, line in enumerate(self.odf_lines_list):

            if self.is_line_with_object_ID(line):
                # line with an object ID
                # recover the object ID without the surrounding brackets
                object_ID = line[1:-1]
                object_ID_str_len = len(object_ID)

                # write in the dictionnary entry of this object ID the index of the line in the ODF lines list
                self.odf_objects_dict[object_ID][IDX_OBJ_LINE] = index

                if object_ID.startswith(('General', 'Manual', 'WindchestGroup', 'Image', 'Label', 'ReversiblePiston', 'SetterElement')):
                    # General999, Manual999, WindchestGroup999, ... object
                    # add a link between 'Organ' (parent) and this object (child)
                    self.objects_dict_append_child('Organ', object_ID)
                elif object_ID.startswith('Panel'):
                    if object_ID_str_len == 8:
                        # Panel999 object
                        # add a link between 'Organ' (parent) and this Panel999 (child)
                        self.objects_dict_append_child('Organ', object_ID)
                    elif object_ID_str_len > 8:
                        # Panel999NNNNN999 object
                        # add a link between Panel999 (parent) and this Panel999NNNNN999 (child)
                        self.objects_dict_append_child(object_ID[0:8], object_ID)

            elif self.is_line_with_attribute(line):
                # line which contains an attribute
                # recover the attribute name and its value (around the equal character)
                (attr_name, attr_value) = line.split("=", 1)

                if attr_name[-3:].isdigit() and attr_value.isdigit():
                    # attribute which ends with 3 digits (like Coupler999) : it contains in its value the reference to another object
                    # add a link between the object ID to which belongs this attribute (parent) and the referenced other object ID (child)
                    self.objects_dict_append_child(object_ID, attr_name[:-3] + attr_value.zfill(3))
                elif attr_name == 'WindchestGroup' and attr_value.isdigit():
                    # attribute WindchestGroup : it contains in its value the reference to a WindchestGroup
                    # add a link between the referenced WindchestGroup (parent) and the object ID to which belongs this attribute (child)
                    self.objects_dict_append_child(attr_name + attr_value.zfill(3), object_ID)
                elif object_ID[8:15] == 'Element' and attr_name in ('Coupler', 'Divisional', 'DivisionalCoupler', 'Enclosure', 'Stop', 'Switch', 'Tremulant'):
                    # panel element of the new panel format with a reference to an object of the main panel
                    # add a link between the object_ID (parent) and the referenced object (child)
                    self.objects_dict_append_child(object_ID, attr_name + attr_value.zfill(3))

                # recover in the attributes a name for the current object
                if (attr_name in ["Name", "ChurchName", "Type", "Image"] or attr_name[-4:] == "Text") and attr_value != "":
                    # the attribute is Name / ChurchName / Type / Image / ...Text and has a value defined
                    if attr_name == "Image":
                        # image attribute, the value is the path of the image : keep from the image path only the file name
                        attr_value = os.path.basename(attr_value)
                    # add the attribute value as name of this object
                    self.objects_dict_append_name(object_ID, attr_value)

        # sort the parents / children lists in each entry of the dictionnary
        for object_ID in self.odf_objects_dict:
            self.odf_objects_dict[object_ID][IDX_OBJ_PAR].sort()
            self.odf_objects_dict[object_ID][IDX_OBJ_CHI].sort()

##        self.objects_dict_save2file('objects_list_dict.txt')

    #-------------------------------------------------------------------------------------------------
    def objects_dict_append_name(self, object_ID, name_to_add):
        #--- append in the objects dictionnary a name for the given object ID

        if object_ID in self.odf_objects_dict:
            # add the given name to the name attribute of the entry of this object
            if len(self.odf_objects_dict[object_ID][IDX_OBJ_NAME]) == 0:
                self.odf_objects_dict[object_ID][IDX_OBJ_NAME] = name_to_add
            else:
                self.odf_objects_dict[object_ID][IDX_OBJ_NAME] = self.odf_objects_dict[object_ID][IDX_OBJ_NAME] + ' | ' + name_to_add
        else:
            pass  # do nothing if the object ID is not present in the dictionnary, this should never happen because the name to add comes from this object

    #-------------------------------------------------------------------------------------------------
    def objects_dict_append_child(self, parent_object_ID, child_object_ID):
        #--- append in the objects dictionnary a link between the given parent / child objects

        if parent_object_ID in self.odf_objects_dict and child_object_ID in self.odf_objects_dict:
            # append the child object_ID to its parent properties
            self.odf_objects_dict[parent_object_ID][IDX_OBJ_CHI].append(child_object_ID)
            # append the parent object_ID to its child properties
            self.odf_objects_dict[child_object_ID][IDX_OBJ_PAR].append(parent_object_ID)

    #-------------------------------------------------------------------------------------------------
    def objects_dict_save2file(self, file_name):
        #--- save the ODF objects dictionnary into the given file (for debug purpose)

        with open(file_name, 'w') as f:
            # write the dictionnary
            f.write('object ID : [object name, parents, children]\n')
            f.write('----------------------------------------\n')
            for obj_ID, obj_prop_list in self.odf_objects_dict.items():
                f.write('%s:%s\n' % (obj_ID, obj_prop_list))

    #-------------------------------------------------------------------------------------------------
    def objects_type_count(self, object_type):
        #--- count the number of objects having the given object type (Manual, Enclosure, ...) in the objects dictionnary with a 3-digits ending index higher than 1
        #--- returns the number of found objects

        counter = 0
        for object_ID in self.odf_objects_dict:
            if object_ID[:-3] == object_type and object_ID[-3:].isdigit():
                if int(object_ID[-3:]) > 0 :
                    counter += 1
                elif object_type not in ('Panel', 'Manual'):
                    self.events_log_add(f"Error : the object identifier {object_ID} cannot have the index 000")
        return counter

    #-------------------------------------------------------------------------------------------------
    def object_get_lines_range(self, object_ID):
        #--- return the indexes range of the object section (ID + attributes) in the ODF lines list
        #--- returns the range (0, 0) if the object ID has not been found

        if object_ID == 'Header':
            # the header of the odf_lines_list
            # set the index to start the search from the beginning of the ODF lines list
            line_idx_first = line_idx_last = 0
        elif object_ID in self.odf_objects_dict:
            # recover in the dictionnary the index of the line where starts the given object ID
            line_idx_first = self.odf_objects_dict[object_ID][IDX_OBJ_LINE]
            # set the index to start the search from the line after the object ID
            line_idx_last = line_idx_first + 1
        else:
            # return a void range since the object_ID is not in the dictionnary
            return (0,0)

        # search for the start of the next object, or the end of odf_lines_list
        while line_idx_last < len(self.odf_lines_list) and not(self.is_line_with_object_ID(self.odf_lines_list[line_idx_last])):
            # no list end and no next object ID reached
            line_idx_last += 1

        if line_idx_last == line_idx_first:
            # no range found
            return (0,0)
        else:
            # range found inside odf_lines_list
            return (line_idx_first, line_idx_last)

    #-------------------------------------------------------------------------------------------------
    def object_get_data_list(self, object_ID):
        #--- return from the ODF lines list the object section lines (object ID + attributes) of the given object ID
        #--- if the object has not be found, return an empty list

        # get the lines range of the object in odf_lines_list
        obj_range = self.object_get_lines_range(object_ID)

        if obj_range != (0, 0):
            return self.odf_lines_list[obj_range[0]:obj_range[1]]
        else:
            return []

    #-------------------------------------------------------------------------------------------------
    def object_get_attribute_value(self, object_ID_or_list, attribute, is_list_sorted = False):
        #--- returns the value (string) of the given attribute defined in the given object ID section of the ODF lines list
        #---   or defined in the given object lines list (which can be sorted, to accelerate the search)
        #--- returns a tuple (attribute value if found else '', index of the attribute in the list if found else -1)

        if isinstance(object_ID_or_list, list):
            # the given parameter is a list
            object_lines_list = object_ID_or_list
        else:
            # the given parameter is an object ID
            # get the lines of the object in the ODF lines list
            object_lines_list = self.object_get_data_list(object_ID_or_list)

        for index, line in enumerate(object_lines_list):
            if self.is_line_with_attribute(line):
                # the line contains an attribute
                # recover the attribute name and value present in this line
                (attr_name, attr_value) = line.split("=", 1)
                if attr_name == attribute:
                    return (attr_value, index)
                elif is_list_sorted and attr_name > attribute:
                    break
        return ('', -1)

    #-------------------------------------------------------------------------------------------------
    def object_get_parent_panel_ID(self, object_ID):
        #--- returns the object ID of the panel (Panel999 or Organ if old panel format) to which belongs the given object ID

        parent_panel_ID = ''

        if object_ID[:5] == 'Panel':
            if len(object_ID) == 8:
                # Panel999 : it has no parent panel
                parent_panel_ID = ''
            else:
                # Panel999NNNNN999
                parent_panel_ID = object_ID[:8]
        else:
            # the object ID is not Panel999 or Panel999Element999, so it is necessarily displayed in the main panel
            if self.new_panel_format:
                parent_panel_ID = 'Panel000'
            else:
                parent_panel_ID = 'Organ'

        return parent_panel_ID

    #-------------------------------------------------------------------------------------------------
    def object_get_parent_manual_ID(self, object_ID):
        #--- returns the object ID of the manual (Manual999) to which belongs the given object ID

        # parse the various Manual999 objects of the dictionnary to see where is referenced the given object ID
        for obj_ID in self.odf_objects_dict:
            if obj_ID[:6] == 'Manual':
                # get the lines of the Manual999 object in the ODF lines list
                object_lines_list = self.object_get_data_list(obj_ID)
                # parse the attributes of this Manual object
                for line in object_lines_list:
                    if self.is_line_with_attribute(line):
                        (attr_name, attr_value) = line.split("=", 1)
                        if attr_name[:-3] == object_ID[:-3] and attr_value.zfill(3) == object_ID[-3:]:
                            # object reference found
                            return obj_ID
        return ''

    #-------------------------------------------------------------------------------------------------
    def object_set_data_list(self, object_ID, new_list):
        #--- replace in odf_lines_list the object section lines (object ID + attributes) of the given object ID
        #--- if the object ID doesn't exist yet, or if object_ID is empty, add it in odf_lines_list
        #--- return the object ID if the set has been done properly, else an empty string

        is_new_list_OK = True
        new_object_ID = object_ID

        if self.is_list_empty(new_list):
            # empty list provided
            if object_ID == 'Header':
                # the empty list is in the header of the ODF
                obj_range = self.object_get_lines_range(object_ID)
                if obj_range != (0, 0):
                    # the header has been found in odf_lines_list, replace it by an empty list
                    self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                    self.events_log_add("Header is now empty")
            else:
                # for any other object ID, we do nothing, there is a special button to delete an object
                self.events_log_add("None data to apply, click on the button Delete to remove an object")
                is_new_list_OK = False
        else:
            # the new list is not empty
            if object_ID == 'Header':
                # special processing if the object is Header, that is the beginning of the odf_lines_list before the first object ID
                # it can contain only comment or empty lines
                # check that the lines of the new list contain only comments or empty lines
                for line in new_list:
                    if len(line) > 0 and line[0] != ';':
                        self.events_log_add(f"Syntax error in the header : '{line}' is not a comment line")
                        is_new_list_OK = False
                if is_new_list_OK:
                    # replace the header section by the new list
                    obj_range = self.object_get_lines_range(object_ID)
                    self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                    self.events_log_add(f"Header updated")

            else:
                # an object section has to be updated or added
                # check the syntax of the new list and the presence of an object ID in its first line
                for index, line in enumerate(new_list):
                    # remove the trailing blank spaces if any
                    line = line.rstrip()
                    if not self.check_odf_line_syntax(line, object_ID):
                        # the line has syntax issue
                        is_new_list_OK = False
                    else:
                        if index == 0:
                            if self.is_line_with_object_ID(line):
                                # the first line contains an object ID, get it
                                new_object_ID = line[1:-1]
                            else:
                                self.events_log_add(f"Syntax error : the first line of the object section must containt an object ID between brackets")
                                is_new_list_OK = False
                        elif self.is_line_with_object_ID(line):
                                self.events_log_add(f"Syntax error : '{line}' an object ID between brackets must be present only in first line of the object section")
                                is_new_list_OK = False

                if is_new_list_OK:
                    # manage the case where the new list contains a new object ID compared to the one given in argument
                    if new_object_ID != object_ID and object_ID != '':
                        self.events_log_add(f"Object {object_ID} unchanged")

                    # recover the range of the object to update in odf_lines_list (if it exists)
                    obj_range = self.object_get_lines_range(new_object_ID)
                    if obj_range != (0, 0):
                        # the object has been found in odf_lines_list, update it with the new list
                        self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                        self.events_log_add(f"Object {new_object_ID} updated")
                    else:
                        # the object doesn't exist in odf_lines_list, add it
                        # add a blank line at the beginning of the new list
                        new_list.insert(0, "")
                        # add the new object in odf_lines_list
                        self.odf_lines_list.extend(new_list)
                        self.events_log_add(f"Object {new_object_ID} added")

                    # update the objects dictionnary
                    self.objects_dict_update()

        return new_object_ID if is_new_list_OK else ''

    #-------------------------------------------------------------------------------------------------
    def object_remove(self, object_ID):
        #--- remove from odf_lines_list the object section lines (object ID + attributes) of the given object ID
        #--- ask to the user to confirm the deletion
        #--- return True or False whether the deletion has been done or not

        obj_removed_ok = False

        if messagebox.askokcancel("ODF Editor", "Do you confirm you want to delete the object " + object_ID + " ?"):
            # the user has accepted the deletion
            # recover the range of the object data
            obj_range = self.object_get_lines_range(object_ID)
            if obj_range != (0, 0):
                # the range has been recovered
                # remove the object section in odf_lines_list
                self.odf_lines_list[obj_range[0]:obj_range[1]] = []
                self.events_log_add(f"Object {object_ID} deleted")
                # update the objects dictionnary
                self.objects_dict_update()
                obj_removed_ok = True
            else:
                self.events_log_add(f"Object {object_ID} not deleted because not found")
                obj_removed_ok = False
        else:
            obj_removed_ok = False

        return obj_removed_ok

    #-------------------------------------------------------------------------------------------------
    def is_list_empty(self, list_to_check):
        #--- returns true or false whether the given list contains only empty items or not

        is_empty = True
        for item in list_to_check:
            if item != '':
                is_empty = False
                break

        return is_empty

    #-------------------------------------------------------------------------------------------------
    def is_line_with_object_ID(self, line_to_check):
        #--- returns True or False whether the given line contains an object ID or not (at least 1 character between brackets)

        return (line_to_check[:1] == "[" and line_to_check[-1:] == "]" and len(line_to_check) > 2)

    #-------------------------------------------------------------------------------------------------
    def is_line_with_attribute(self, line_to_check):
        #--- returns True or False whether the given line contains an object attribute or not (at least 3 characters with '=' present not in first position and ';' not in first position)

        return (len(line_to_check) > 3 and line_to_check[0] != ';' and line_to_check[0] != '=' and '=' in line_to_check)

    #-------------------------------------------------------------------------------------------------
    def check_odf_line_syntax(self, line, line_location):
        #--- returns True/False whether the given line string respects the ODF syntax or not
        #--- insert the given line location information in the error log if an error is detected
        #--- the given line string must not have leading/trailing whitespaces (let use str.strip() function on it before the call)

        syntax_is_OK = True

        if line[:1] == "[":  # line normally with an object ID
            if line[-1:] != "]":  # object ID without closing bracket
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character ']' is missing at the end to define an object ID")
                syntax_is_OK = False
            elif len(line) < 3:   # object ID with no string between the brackets
                self.events_log_add(f"Syntax error in {line_location} '{line}' : an object ID must be defined between the brackets")
                syntax_is_OK = False
            elif not line[1:-1].isalnum():  # object ID not containing only alphanumeric characters
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the object ID must contain only alphanumeric characters")
                syntax_is_OK = False

        elif len(line) > 0 and line[:1] != ";":  # it is not an empty or comment line
            if '=' not in line:    # none equal character in the line
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character '=' is missing to define an attribute=value pair or it may be a comment line")
                syntax_is_OK = False
            elif line[:1] == '=':  # the line starts by an equal character
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character '=' must not start a line")
                syntax_is_OK = False
            else:
                attr_name = line.rpartition("=")[0]  # recover the attribute at the left of =
                for char in attr_name:
                    if char not in ALLOWED_CHARS_4_FIELDS:
                        self.events_log_add(f"Syntax error in {line_location} '{line}' : the attribute '{attr_name}' must contain only alphanumeric or '_' characters")
                        syntax_is_OK = False
                        break

        return syntax_is_OK

    #-------------------------------------------------------------------------------------------------
    def check_odf_lines(self, update_call_back_fct):
        #--- check the consistency of the data which are present in odf_lines_list

        if self.check_files_names == '':
            # ask the user if he wants to check the files names
            self.check_files_names = messagebox.askyesno("ODF Editor", "Do you want to check the files names ? \nThis choice will be kept until the next ODF opening")

        self.check_nb_attr = 0

        # update the panel format flag
        self.check_odf_panel_format()

        # check the syntax of the header of the ODF
        object_lines_list = self.object_get_data_list('Header')
        for line in object_lines_list:
            self.check_odf_line_syntax(line, "the header")

        # check the presence of the Organ object (which is the root of all the other objects)
        if 'Organ' not in self.odf_objects_dict:
            self.events_log_add("Error : the object Organ is not defined")

        for object_ID in self.odf_objects_dict:
            # parse the objects of the objects dictionnary keys

            # recover the lines of the object section in odf_lines_list
            object_lines_list = self.object_get_data_list(object_ID)

            # update in the GUI the name of the checked object ID
            update_call_back_fct(object_ID)

            if len(object_lines_list) > 0:
                # lines have been recovered for the current object ID

                # check the syntax of the lines of the object
                for line in object_lines_list:
                    self.check_odf_line_syntax(line, object_ID)

                # remove the first line of the object section which contains the object ID
                object_lines_list.pop(0)

                # sort the lines list to make faster the search which is done in check_attribute_value
                object_lines_list.sort()

                # remove the first line while it is empty (after the sorting the empty lines are all in first positions)
                while object_lines_list[0] == '':
                    object_lines_list.pop(0)

                # check if the attributes are all uniques in the object section
                self.check_attributes_unicity(object_ID, object_lines_list)

                # generate the generic object ID (Manual999 instead of Manual001 for example)
                gen_object_ID = ''
                for c in object_ID:
                    gen_object_ID += '9' if c.isdigit() else c

                # check the attributes and values of the object
                if gen_object_ID == 'Organ':
                    self.check_object_Organ(object_ID, object_lines_list)
                elif gen_object_ID == 'Coupler999':
                    self.check_object_Coupler(object_ID, object_lines_list)
                elif gen_object_ID == 'Divisional999':
                    self.check_object_Divisional(object_ID, object_lines_list)
                elif gen_object_ID == 'DivisionalCoupler999':
                    self.check_object_DivisionalCoupler(object_ID, object_lines_list)
                elif gen_object_ID == 'Enclosure999':
                    self.check_object_Enclosure(object_ID, object_lines_list)
                elif gen_object_ID == 'General999':
                    self.check_object_General(object_ID, object_lines_list)
                elif gen_object_ID == 'Image999':
                    self.check_object_Image(object_ID, object_lines_list)
                elif gen_object_ID == 'Label999':
                    self.check_object_Label(object_ID, object_lines_list)
                elif gen_object_ID == 'Manual999':
                    self.check_object_Manual(object_ID, object_lines_list)
                elif gen_object_ID == 'Panel999':
                    self.check_object_Panel(object_ID, object_lines_list)
                elif gen_object_ID == 'Panel999Element999':
                    self.check_object_PanelElement(object_ID, object_lines_list)
                elif gen_object_ID[:5] == 'Panel': # Panel999Coupler999, Panel999Divisional999, Panel999Image999, ...
                    self.check_object_PanelOther(object_ID, object_lines_list)
                elif gen_object_ID == 'Rank999':
                    self.check_object_Rank(object_ID, object_lines_list)
                elif gen_object_ID == 'ReversiblePiston999':
                    self.check_object_ReversiblePiston(object_ID, object_lines_list)
                elif gen_object_ID == 'SetterElement999':
                    self.check_object_SetterElement(object_ID, object_lines_list)
                elif gen_object_ID == 'Stop999':
                    self.check_object_Stop(object_ID, object_lines_list)
                elif gen_object_ID == 'Switch999':
                    self.check_object_Switch(object_ID, object_lines_list)
                elif gen_object_ID == 'Tremulant999':
                    self.check_object_Tremulant(object_ID, object_lines_list)
                elif gen_object_ID == 'WindchestGroup999':
                    self.check_object_WindchestGroup(object_ID, object_lines_list)
                else:
                    # the object ID has not been recognized
                    self.events_log_add(f"Error : the object identifier {object_ID} is invalid or misspelled")
                    # empty the lines list of the object which is not recognized, to not display in the log its attributes which have not been checked
                    object_lines_list = []

                # report in the logs if attributes have not been recognized in the object section, so they are not expected or are misspelled
                # each attribute checked by the function check_attribute_value() has been removed in the lines list after its check
                # so the one still in the list have not been recognized by the check_object_xxx functions called before
                for line in object_lines_list:
                    if self.is_line_with_attribute(line):
                        self.check_nb_attr += 1
                        (attr_name, attr_value) = line.split("=", 1)
                        self.events_log_add(f"Warning in {object_ID} : the attribute {attr_name} is not expected in this object or is misspelled or please fix an error above")

        # report in the logs if Couplers / Divisionals / Stops are referenced in none object (Manual or WindchestGroup), so they are not used
        for obj_ID, obj_prop_list in self.odf_objects_dict.items():
            if obj_ID != 'Organ' and len(obj_prop_list[IDX_OBJ_PAR]) == 0:
                # the object has none parent in the objects dictionnary
                self.events_log_add(f"Warning : the object {obj_ID} is not used")

        # display in the log the number of checked attributes
        self.events_log_add(f"{self.check_nb_attr} attributes checked")

        # display in the log if none error has been detected
        if len(self.events_log_list) <= 3:  # 3 lines minimum : check start message + detected panel format + number of checked attributes
            self.events_log_add("None error found")

    #-------------------------------------------------------------------------------------------------
    def check_odf_panel_format(self):
        #--- check which is the panel format used in the ODF (new or old) and update the flag

        (attr_value, attr_idx) = self.object_get_attribute_value('Panel000', 'NumberOfGUIElements')
        self.new_panel_format = (attr_value.isdigit() and int(attr_value) >= 0)

        if self.new_panel_format:
            self.events_log_add("New panel format detected")
        else:
            self.events_log_add("Old panel format detected")

    #-------------------------------------------------------------------------------------------------
    def check_object_Organ(self, object_ID, lines_list):
        #--- check the data of an Organ object section which the lines are in the given lines list

        # required attributes
        self.check_attribute_value(object_ID, lines_list, 'ChurchName', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_ID, lines_list, 'ChurchAddress', ATTR_TYPE_STRING, True)

        ret = self.check_attribute_value(object_ID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)
        if ret == "Y" and not ('Manual000' in self.odf_objects_dict):
            self.events_log_add(f"Error in {object_ID} : HasPedals=Y but no Manual000 object is defined")
        elif ret == "N" and ('Manual000' in self.odf_objects_dict):
            self.events_log_add(f"Error in {object_ID} : HasPedals=N whereas a Manual000 object is defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, True, 0, 8)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('DivisionalCoupler')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfDivisionalCouplers={ret} whereas {count} DivisionalCoupler object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, 50)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Enclosure')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfEnclosures={ret} whereas {count} Enclosure object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfGenerals', ATTR_TYPE_INTEGER, True, 0, 99)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('General')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfGenerals={ret} whereas {count} General object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 1, 16)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Manual')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfManuals={ret} whereas {count} Manual object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfPanels', ATTR_TYPE_INTEGER, self.new_panel_format, 0, 100)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Panel')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfPanels={ret} whereas {count} Panel object(s) defined")

        if self.new_panel_format and not ('Panel000' in self.odf_objects_dict):
            self.events_log_add(f"Error : new panel format used but no Panel000 object is defined")
        elif not self.new_panel_format and ('Panel000' in self.odf_objects_dict):
            self.events_log_add(f"Error in {object_ID} : old panel format used whereas a Panel000 is defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfReversiblePistons', ATTR_TYPE_INTEGER, True, 0, 32)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('ReversiblePiston')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfReversiblePistons={ret} whereas {count} ReversiblePiston object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, 10)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Tremulant')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfTremulants={ret} whereas {count} Tremulant object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfWindchestGroups', ATTR_TYPE_INTEGER, True, 1, 50)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('WindchestGroup')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfWindchestGroups={ret} whereas {count} WindchestGroup object(s) defined")

        self.check_attribute_value(object_ID, lines_list, 'DivisionalsStoreIntermanualCouplers', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DivisionalsStoreIntramanualCouplers', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DivisionalsStoreTremulants', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'GeneralsStoreDivisionalCouplers', ATTR_TYPE_BOOLEAN, True)

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'OrganBuilder', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'OrganBuildDate', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'OrganComments', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'RecordingDetails', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'InfoFilename', ATTR_TYPE_STRING, False)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, False, 0, 999) # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Image')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfImages={ret} whereas {count} Image object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfLabels', ATTR_TYPE_INTEGER, False, 0, 999)  # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Label')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfLabels={ret} whereas {count} Label object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfRanks', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Rank')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfRanks={ret} whereas {count} Rank object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSetterElements', ATTR_TYPE_INTEGER, False, 0, 999)  # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('SetterElement')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfSetterElements={ret} whereas {count} SetterElement object(s) defined")

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Switch')
            if count != int(ret):
                self.events_log_add(f"Error in {object_ID} : NumberOfSwitches={ret} whereas {count} Switch object(s) defined")

        self.check_attribute_value(object_ID, lines_list, 'CombinationsStoreNonDisplayedDrawstops', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_ID, lines_list, 'Gain', ATTR_TYPE_FLOAT, False, -120, 40)
        self.check_attribute_value(object_ID, lines_list, 'PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_ID, lines_list, 'TrackerDelay', ATTR_TYPE_FLOAT, False, 0, 10000)

        if not self.new_panel_format:
            # if old parnel format, the Organ object contains panel attributes
            self.check_object_Panel(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Button(self, object_ID, lines_list):
        #--- check the data of a Button object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'ShortcutKey', ATTR_TYPE_INTEGER, False, 0, 255)
        self.check_attribute_value(object_ID, lines_list, 'StopControlMIDIKeyNumber', ATTR_TYPE_INTEGER, False, 0, 127)
        self.check_attribute_value(object_ID, lines_list, 'MIDIProgramChangeNumber', ATTR_TYPE_INTEGER, False, 1, 128)
        self.check_attribute_value(object_ID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DisplayInInvertedState', ATTR_TYPE_BOOLEAN, False)

        display_as_piston = self.check_attribute_value(object_ID, lines_list, 'DisplayAsPiston', ATTR_TYPE_BOOLEAN, False)
        if display_as_piston == '':
            # attribute not defined, set its default value
            if (any(str in object_ID for str in ('Divisional', 'General')) or
                ('Element' in object_ID and any(str in self.object_get_attribute_value(object_ID, 'Type') for str in ('Divisional', 'General')))):
                # the object is a Divisional or General button or GUI element, so it must be displayed as a piston by default
                display_as_piston = 'Y'
            else:
                display_as_piston = 'N'

        self.check_attribute_value(object_ID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelText', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'DispKeyLabelOnLeft', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DispImageNum', ATTR_TYPE_INTEGER, False, 1, 5 if display_as_piston == 'Y' else 6)
        self.check_attribute_value(object_ID, lines_list, 'DispButtonRow', ATTR_TYPE_INTEGER, False, 0, 199)
        self.check_attribute_value(object_ID, lines_list, 'DispButtonCol', ATTR_TYPE_INTEGER, False, 1, 32)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopRow', ATTR_TYPE_INTEGER, False, 1, 199)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopCol', ATTR_TYPE_INTEGER, False, 1, 12)
        image_on = self.check_attribute_value(object_ID, lines_list, 'ImageOn', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_ID, lines_list, 'ImageOff', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_ID, lines_list, 'MaskOn', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_ID, lines_list, 'MaskOff', ATTR_TYPE_FILE_NAME, False)

        # get the dimensions of the parent panel
        panel_ID = self.object_get_parent_panel_ID(object_ID)
        (value, idx) = self.object_get_attribute_value(panel_ID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(panel_ID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_ID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_ID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_ID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        # get the dimensions of the button bitmap
        if image_on != '':
            # an image is defined to display the button
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image_on.replace('\\', '/')
                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = photo.width()
                bitmap_height = photo.height()
            else:
                bitmap_width = 500  # arbritrary default value
                bitmap_height = 200 # arbritrary default value
        else:
            # no image file defined, get the dimensions of the internal bitmap (piston or drawstop)
            if display_as_piston == 'Y':
                bitmap_width = bitmap_height = 32
            else:
                bitmap_width = bitmap_height = 62

        self.check_attribute_value(object_ID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_ID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_ID, lines_list, 'MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'MouseRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        mouse_rect_width = self.check_attribute_value(object_ID, lines_list, 'MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        mouse_rect_height = self.check_attribute_value(object_ID, lines_list, 'MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if mouse_rect_width.isdigit() and mouse_rect_height.isdigit():
            mouse_radius = max(int(mouse_rect_width), int(mouse_rect_height))
        else:
            mouse_radius = max(bitmap_width, bitmap_height)
        self.check_attribute_value(object_ID, lines_list, 'MouseRadius', ATTR_TYPE_INTEGER, False, 0, mouse_radius)

        self.check_attribute_value(object_ID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_ID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_ID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_Coupler(self, object_ID, lines_list):
        #--- check the data of a Coupler object section which the lines are in the given lines list

        # required attributes
        ret1 = self.check_attribute_value(object_ID, lines_list, 'UnisonOff', ATTR_TYPE_BOOLEAN, True)
        ret2 = self.check_attribute_value(object_ID, lines_list, 'CouplerType', ATTR_TYPE_COUPLER_TYPE, False)  # optional but here to recover its value used after
        self.check_attribute_value(object_ID, lines_list, 'DestinationManual', ATTR_TYPE_INTEGER, True if ret1 == 'N' else False, 0, 16) # conditional required/optional
        self.check_attribute_value(object_ID, lines_list, 'DestinationKeyshift', ATTR_TYPE_INTEGER, True if ret1 == 'N' else False, -24, 24) # conditional required/optional

        is_required = (ret1 == 'N' and not(ret2.upper() in ('MELODY', 'BASS')))
        self.check_attribute_value(object_ID, lines_list, 'CoupleToSubsequentUnisonIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_ID, lines_list, 'CoupleToSubsequentUpwardIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_ID, lines_list, 'CoupleToSubsequentDownwardIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_ID, lines_list, 'CoupleToSubsequentUpwardIntramanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_ID, lines_list, 'CoupleToSubsequentDownwardIntramanualCouplers', ATTR_TYPE_BOOLEAN, is_required)

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'FirstMIDINoteNumber', ATTR_TYPE_INTEGER, False, 0, 127)
        self.check_attribute_value(object_ID, lines_list, 'NumberOfKeys', ATTR_TYPE_INTEGER, False, 0, 127)

        # a Coupler has in addition the attributes of a DrawStop
        self.check_object_DrawStop(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Divisional(self, object_ID, lines_list):
        #--- check the data of a Divisional object section which the lines are in the given lines list

        # recover the ID of manual in which is referenced this Divisional
        parent_manual_ID = self.object_get_parent_manual_ID(object_ID)

        # required attributes
        (ret, idx) = self.object_get_attribute_value(parent_manual_ID, 'NumberOfCouplers')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Coupler{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        (ret, idx) = self.object_get_attribute_value(parent_manual_ID, 'NumberOfStops')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Stop{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        (ret, idx) = self.object_get_attribute_value(parent_manual_ID, 'NumberOfTremulants')
        max = int(ret) if ret.isdigit() else 10
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Protected', ATTR_TYPE_BOOLEAN, False)

        (ret, idx) = self.object_get_attribute_value(parent_manual_ID, 'NumberOfSwitches')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Switch{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # a Divisional has in addition the attributes of a Push Button
        self.check_object_PushButton(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_DivisionalCoupler(self, object_ID, lines_list):
        #--- check the data of a Divisional Coupler object section which the lines are in the given lines list

        # required attributes
        self.check_attribute_value(object_ID, lines_list, 'BiDirectionalCoupling', ATTR_TYPE_BOOLEAN, True)

        (ret, idx) = self.object_get_attribute_value('Organ', 'NumberOfManuals')
        max = int(ret) if ret.isdigit() else 16
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 1, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f"Manual{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)

        # a Divisional Coupler has in addition the attributes of a DrawStop
        self.check_object_DrawStop(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_DrawStop(self, object_ID, lines_list):
        #--- check the data of a DrawStop object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Function', ATTR_TYPE_DRAWSTOP_FCT, False)

        (ret, idx) = self.object_get_attribute_value('Organ', 'NumberOfSwitches')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_ID, lines_list, 'SwitchCount', ATTR_TYPE_INTEGER, False, 1, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f"Switch{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)

        self.check_attribute_value(object_ID, lines_list, 'DefaultToEngaged', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'GCState', ATTR_TYPE_INTEGER, False, -1, 1)
        self.check_attribute_value(object_ID, lines_list, 'StoreInDivisional', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'StoreInGeneral', ATTR_TYPE_BOOLEAN, False)

        # a Drawstop has in addition the attributes of a Button
        self.check_object_Button(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Enclosure(self, object_ID, lines_list):
        #--- check the data of an Enclosure object section which the lines are in the given lines list

        # required attributes
        # none required attribute

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'AmpMinimumLevel', ATTR_TYPE_INTEGER, False, 0, 100)
        self.check_attribute_value(object_ID, lines_list, 'MIDIInputNumber', ATTR_TYPE_INTEGER, False, 0, 100)
        self.check_attribute_value(object_ID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelText', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_ID, lines_list, 'EnclosureStyle', ATTR_TYPE_INTEGER, False, 1, 4)

        ret = self.check_attribute_value(object_ID, lines_list, 'BitmapCount', ATTR_TYPE_INTEGER, False, 1, 127)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                image = self.check_attribute_value(object_ID, lines_list, f'Bitmap{str(idx).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                self.check_attribute_value(object_ID, lines_list, f'Mask{str(idx).zfill(3)}', ATTR_TYPE_FILE_NAME, False)
            # get the dimensions of the last enclosure bitmap
            if image != '' and self.check_files_names:
                # an image is defined to display the enclosure
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = photo.width()
                bitmap_height = photo.height()
            else:
                bitmap_width = 100  # arbritrary default value
                bitmap_height = 200 # arbritrary default value
        else:
            # no image file defined, get the dimensions of the internal bitmap
            bitmap_width = 46
            bitmap_height = 61

        # get the dimensions of the parent panel
        panel_ID = self.object_get_parent_panel_ID(object_ID)
        (value, idx) = self.object_get_attribute_value(panel_ID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(panel_ID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_ID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_ID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_ID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        self.check_attribute_value(object_ID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_ID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_ID, lines_list, 'MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'MouseRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        self.check_attribute_value(object_ID, lines_list, 'MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        mouse_rect_height = self.check_attribute_value(object_ID, lines_list, 'MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if mouse_rect_height.isdigit():
            max_start = int(mouse_rect_height)
        else:
            max_start = 200
        mouse_axis_start = self.check_attribute_value(object_ID, lines_list, 'MouseAxisStart', ATTR_TYPE_INTEGER, False, 0, max_start)

        if mouse_axis_start.isdigit():
            min_end = int(mouse_axis_start)
        else:
            min_end = 200
        self.check_attribute_value(object_ID, lines_list, 'MouseAxisEnd', ATTR_TYPE_INTEGER, False, min_end, max_start)

        self.check_attribute_value(object_ID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_ID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_ID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_General(self, object_ID, lines_list):
        #--- check the data of a General object section which the lines are in the given lines list

        is_general_obj = object_ID.startswith('General') # some mandatory attributes are not mandatory for objects which inherit the General attributes

        # required attributes
        max = self.objects_type_count('Coupler')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'CouplerNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_ID, lines_list, f'CouplerManual{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('DivisionalCoupler')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'DivisionalCouplerNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Stop')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'StopNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_ID, lines_list, f'StopManual{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'TremulantNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        max = self.objects_type_count('Switch')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'SwitchNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        self.check_attribute_value(object_ID, lines_list, 'Protected', ATTR_TYPE_BOOLEAN, False)

        # a General has in addition the attributes of a Push Button
        self.check_object_PushButton(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Image(self, object_ID, lines_list):
        #--- check the data of an Image object section which the lines are in the given lines list

        # required attributes
        image = self.check_attribute_value(object_ID, lines_list, 'Image', ATTR_TYPE_FILE_NAME, True)

        # get the dimensions of the parent panel
        parent_panel_ID = self.object_get_parent_panel_ID(object_ID)
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Mask', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_ID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        self.check_attribute_value(object_ID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)

        # get the dimensions of the image bitmap
        if image != '':
            # an image is defined
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = photo.width()
                bitmap_height = photo.height()
            else:
                bitmap_width = panel_width
                bitmap_height = panel_height
        else:
            # no image file defined
            bitmap_width = panel_width
            bitmap_height = panel_height

        self.check_attribute_value(object_ID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_ID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

    #-------------------------------------------------------------------------------------------------
    def check_object_Label(self, object_ID, lines_list):
        #--- check the data of a Label object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        ret1 = self.check_attribute_value(object_ID, lines_list, 'FreeXPlacement', ATTR_TYPE_BOOLEAN, False)
        ret2 = self.check_attribute_value(object_ID, lines_list, 'FreeYPlacement', ATTR_TYPE_BOOLEAN, False)

        # get the dimensions of the parent panel
        parent_panel_ID = self.object_get_parent_panel_ID(object_ID)
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_ID, lines_list, 'DispXpos', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'DispYpos', ATTR_TYPE_INTEGER, False, 0, panel_height)

        self.check_attribute_value(object_ID, lines_list, 'DispAtTopOfDrawstopCol', ATTR_TYPE_BOOLEAN, ret2 == 'N')

        # get the number of drawstop columns in the parent panel
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispDrawstopCols')
        columns_nb = int(value) if value.isdigit() else 12
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopCol', ATTR_TYPE_INTEGER, ret1 == 'N', 1, columns_nb)

        self.check_attribute_value(object_ID, lines_list, 'DispSpanDrawstopColToRight', ATTR_TYPE_BOOLEAN, True if ret1 == 'N' else False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_ID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        image_num = self.check_attribute_value(object_ID, lines_list, 'DispImageNum', ATTR_TYPE_INTEGER, False, 1, 12)
        image = self.check_attribute_value(object_ID, lines_list, 'Image', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_ID, lines_list, 'Mask', ATTR_TYPE_FILE_NAME, False)

        self.check_attribute_value(object_ID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_ID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_ID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        # get the dimensions of the label bitmap
        if image != '':
            # an image is defined to display the label
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = photo.width()
                bitmap_height = photo.height()
            else:
                bitmap_width = 400  # arbritrary default value
                bitmap_height = 100 # arbritrary default value
        else:
            if   image_num == '1':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '2':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '3':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '4':  bitmap_width = 160; bitmap_height = 25
            elif image_num == '5':  bitmap_width = 200; bitmap_height = 50
            elif image_num == '6':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '7':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '8':  bitmap_width = 160; bitmap_height = 25
            elif image_num == '9':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '10': bitmap_width = 80; bitmap_height = 25
            elif image_num == '11': bitmap_width = 160; bitmap_height = 25
            else:                   bitmap_width = 200; bitmap_height = 50


        self.check_attribute_value(object_ID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_ID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_ID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_ID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_ID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_ID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_Manual(self, object_ID, lines_list):
        #--- check the data of a Manual object section which the lines are in the given lines list

        is_manual_obj = object_ID.startswith('Manual') # some mandatory attributes are not mandatory for objects which inherit the Manual attributes

        # required attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, is_manual_obj)
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfLogicalKeys', ATTR_TYPE_INTEGER, is_manual_obj, 1, 192)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                # attributes Key999xxx
                image = self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}ImageOn', ATTR_TYPE_FILE_NAME, False)
                if image != "":
                    # check the other attributes for this key only if an image on is defined
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}ImageOff', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MaskOn', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MaskOff', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}Width', ATTR_TYPE_INTEGER, False, 0, 500)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}Offset', ATTR_TYPE_INTEGER, False, -500, 500)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}YOffset', ATTR_TYPE_INTEGER, False, 0, 500)

                    # get the dimensions of the key bitmap
                    # an image is defined to display the key
                    if self.check_files_names:
                        # get the sizes of the image in the file which is existing
                        modif_path = image.replace('\\', '/')
                        photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
                        bitmap_width = photo.width()
                        bitmap_height = photo.height()
                    else:
                        bitmap_width = 100  # arbritrary default value
                        bitmap_height = 300 # arbritrary default value

                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MouseRectTop', ATTR_TYPE_INTEGER, False, 0, bitmap_height)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
                    self.check_attribute_value(object_ID, lines_list, f'Key{str(idx).zfill(3)}MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        logical_keys_nb = int(ret) if ret.isdigit() else 192
        self.check_attribute_value(object_ID, lines_list, 'FirstAccessibleKeyLogicalKeyNumber', ATTR_TYPE_INTEGER, is_manual_obj, 1, logical_keys_nb)
        self.check_attribute_value(object_ID, lines_list, 'FirstAccessibleKeyMIDINoteNumber', ATTR_TYPE_INTEGER, is_manual_obj, 0, 127)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfAccessibleKeys', ATTR_TYPE_INTEGER, is_manual_obj, 0, 85)
        accessible_keys_nb = int(ret) if ret.isdigit() else 85

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Coupler{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfDivisionals', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Divisional{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Stop{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Switch')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Switch{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        for idx in range(0, 128):
            self.check_attribute_value(object_ID, lines_list, f'MIDIKey{str(idx).zfill(3)}', ATTR_TYPE_INTEGER, False, 0, 127)

        self.check_attribute_value(object_ID, lines_list, 'MIDIInputNumber', ATTR_TYPE_INTEGER, False, 0, 200)
        self.check_attribute_value(object_ID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)

        # get the dimensions of the parent panel
        parent_panel_ID = self.object_get_parent_panel_ID(object_ID)
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_ID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_ID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_ID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)

        self.check_attribute_value(object_ID, lines_list, 'DispKeyColourInverted', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DispKeyColourWooden', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DisplayFirstNote', ATTR_TYPE_INTEGER, False, 0, 127)

        ret = self.check_attribute_value(object_ID, lines_list, 'DisplayKeys', ATTR_TYPE_INTEGER, False, 1, accessible_keys_nb)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'DisplayKey{str(idx).zfill(3)}', ATTR_TYPE_INTEGER, False, 0, 127)
                self.check_attribute_value(object_ID, lines_list, f'DisplayKey{str(idx).zfill(3)}Note', ATTR_TYPE_INTEGER, False, 0, 127)

        # optional attributes with the KEYTYPE format
        ImageOn_First_keytype = '' # variable to store if the first attribute have been already checked for the ImageOn key type
        ImageOff_First_keytype = ''
        MaskOn_First_keytype = ''
        MaskOff_First_keytype = ''
        Width_First_keytype = ''
        Offset_First_keytype = ''
        YOffset_First_keytype = ''

        ImageOn_Last_keytype = ''
        ImageOff_Last_keytype = ''
        MaskOn_Last_keytype = ''
        MaskOff_Last_keytype = ''
        Width_Last_keytype = ''
        Offset_Last_keytype = ''
        YOffset_Last_keytype = ''

        for keytype in ('C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'B'):
            if self.check_attribute_value(object_ID, lines_list, f'ImageOn_{keytype}', ATTR_TYPE_FILE_NAME, False) == '':
                # if there is no ImageOn_C attribute in the object so we can skip the other KEYTYPE attributes checks to not waste checking time
                break
            self.check_attribute_value(object_ID, lines_list, f'ImageOff_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_ID, lines_list, f'MaskOn_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_ID, lines_list, f'MaskOff_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_ID, lines_list, f'Width_{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            self.check_attribute_value(object_ID, lines_list, f'Offset_{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            self.check_attribute_value(object_ID, lines_list, f'YOffset_{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            # the First and Last attributes are checked only once for each key property
            # so if there is more than one First or Last definition it will appear in the warning logs because it will not have been checked here
            if ImageOn_First_keytype == '' : ImageOn_First_keytype = self.check_attribute_value(object_ID, lines_list, f'ImageOn_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if ImageOff_First_keytype == '' : ImageOff_First_keytype = self.check_attribute_value(object_ID, lines_list, f'ImageOff_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOn_First_keytype == '' : MaskOn_First_keytype = self.check_attribute_value(object_ID, lines_list, f'MaskOn_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOff_First_keytype == '' : MaskOff_First_keytype = self.check_attribute_value(object_ID, lines_list, f'MaskOff_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if Width_First_keytype == '' : Width_First_keytype = self.check_attribute_value(object_ID, lines_list, f'Width_First{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            if Offset_First_keytype == '' : Offset_First_keytype = self.check_attribute_value(object_ID, lines_list, f'Offset_First{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            if YOffset_First_keytype == '' : YOffset_First_keytype = self.check_attribute_value(object_ID, lines_list, f'YOffset_First{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)

            if ImageOn_Last_keytype == '' : ImageOn_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'ImageOn_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if ImageOff_Last_keytype == '' : ImageOff_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'ImageOff_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOn_Last_keytype == '' : MaskOn_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'MaskOn_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOff_Last_keytype == '' : MaskOff_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'MaskOff_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if Width_Last_keytype == '' : Width_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'Width_Last{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            if Offset_Last_keytype == '' : Offset_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'Offset_Last{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            if YOffset_Last_keytype == '' : YOffset_Last_keytype = self.check_attribute_value(object_ID, lines_list, f'YOffset_Last{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)

    #-------------------------------------------------------------------------------------------------
    def check_object_Panel(self, object_ID, lines_list):
        #--- check the data of a Panel object section which the lines are in the given lines list

        is_additional_panel = not(object_ID in ('Panel000', 'Organ')) # it is an additional panel, in addition to the Panel000 or Organ (old format) panel

        if self.new_panel_format:

            # required attributes (new panel format)
            self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, is_additional_panel)
            self.check_attribute_value(object_ID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfGUIElements', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_ID}Element')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfGUIElements={ret} whereas {count} {object_ID}Element object(s) defined")

            # optional attributes (new panel format)
            self.check_attribute_value(object_ID, lines_list, 'Group', ATTR_TYPE_STRING, False)

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, False, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_ID}Image')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfImages={ret} whereas {count} {object_ID}Image object(s) defined")

        elif is_additional_panel:  # additional panel in the old panel format (for the main panel, the non display metrics attributes are defined in the Organ object)

            # required attributes (old panel format, additional panel)
            self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, True)
            self.check_attribute_value(object_ID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Coupler{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_ID, lines_list, f"Coupler{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Coupler')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfCouplers={ret} whereas {count} {object_ID}Coupler object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfDivisionals', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Divisional{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_ID, lines_list, f"Divisional{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Divisional')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfDivisionals={ret} whereas {count} {object_ID}Divisional object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, True, 0, 8)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"DivisionalCoupler{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}DivisionalCoupler')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfDivisionalCouplers={ret} whereas {count} {object_ID}DivisionalCoupler object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, 50)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Enclosure{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Enclosure')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfEnclosures={ret} whereas {count} {object_ID}Enclosure object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfGenerals', ATTR_TYPE_INTEGER, True, 0, 99)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"General{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}General')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfGenerals={ret} whereas {count} {object_ID}General object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_ID}Image')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfImages={ret} whereas {count} {object_ID}Image object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfLabels', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_ID}Label')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfLabels={ret} whereas {count} {object_ID}Label object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 0, 16)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Manual{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfReversiblePistons', ATTR_TYPE_INTEGER, True, 0, 32)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"ReversiblePiston{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}ReversiblePiston')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfReversiblePistons={ret} whereas {count} {object_ID}ReversiblePiston object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Stop{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_ID, lines_list, f"Stop{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Stop')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfStops={ret} whereas {count} {object_ID}Stop object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, 10)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Tremulant{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Tremulant')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfTremulants={ret} whereas {count} {object_ID}Tremulant object(s) defined")

            # optional attributes (old panel format, additional panel)
            self.check_attribute_value(object_ID, lines_list, 'Group', ATTR_TYPE_STRING, False)

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSetterElements', ATTR_TYPE_INTEGER, False, 0, 8)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_ID}SetterElement')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfSetterElements={ret} whereas {count} {object_ID}SetterElement object(s) defined")

            ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_ID, lines_list, f"Switch{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_ID}Switch')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_ID} : NumberOfSwitches={ret} whereas {count} {object_ID}Switch object(s) defined")


        # display metrics (common to old and new panel formats)

        # required attributes (panel display metrics)
        self.check_attribute_value(object_ID, lines_list, 'DispScreenSizeHoriz', ATTR_TYPE_PANEL_SIZE, True)
        self.check_attribute_value(object_ID, lines_list, 'DispScreenSizeVert', ATTR_TYPE_PANEL_SIZE, True)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_ID, lines_list, 'DispConsoleBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_ID, lines_list, 'DispKeyHorizBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_ID, lines_list, 'DispKeyVertBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopInsetBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_ID, lines_list, 'DispControlLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_ID, lines_list, 'DispShortcutKeyLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_ID, lines_list, 'DispShortcutKeyLabelColour', ATTR_TYPE_COLOR, True)
        self.check_attribute_value(object_ID, lines_list, 'DispGroupLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopCols', ATTR_TYPE_INTEGER, True, 2, 12)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopRows', ATTR_TYPE_INTEGER, True, 1, 20)
        cols_offset = self.check_attribute_value(object_ID, lines_list, 'DispDrawstopColsOffset', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispPairDrawstopCols', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraDrawstopRows', ATTR_TYPE_INTEGER, True, 0, 99)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraDrawstopCols', ATTR_TYPE_INTEGER, True, 0, 40)
        self.check_attribute_value(object_ID, lines_list, 'DispButtonCols', ATTR_TYPE_INTEGER, True, 1, 32)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraButtonRows', ATTR_TYPE_INTEGER, True, 0, 99)
        extra_pedal_buttons = self.check_attribute_value(object_ID, lines_list, 'DispExtraPedalButtonRow', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispButtonsAboveManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraDrawstopRowsAboveExtraButtonRows', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispTrimAboveManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispTrimBelowManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_ID, lines_list, 'DispTrimAboveExtraRows', ATTR_TYPE_BOOLEAN, True)

        # optional attributes (panel display metrics)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispDrawstopOuterColOffsetUp', ATTR_TYPE_BOOLEAN, True if cols_offset == 'Y' else False)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraPedalButtonRowOffset', ATTR_TYPE_BOOLEAN, True if extra_pedal_buttons == 'Y' else False)
        self.check_attribute_value(object_ID, lines_list, 'DispExtraPedalButtonRowOffsetRight', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_ID, lines_list, 'DispPistonWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispPistonHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispEnclosureWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispEnclosureHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_ID, lines_list, 'DispPedalHeight', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_ID, lines_list, 'DispPedalKeyWidth', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_ID, lines_list, 'DispManualHeight', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_ID, lines_list, 'DispManualKeyWidth', ATTR_TYPE_INTEGER, False, 1, 500)

    #-------------------------------------------------------------------------------------------------
    def check_object_PanelElement(self, object_ID, lines_list):
        #--- check the data of a Panel Element object section which the lines are in the given lines list

        # required attributes
        type = self.check_attribute_value(object_ID, lines_list, 'Type', ATTR_TYPE_ELEMENT_TYPE, True)

        if type == 'Coupler':
            self.check_attribute_value(object_ID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_ID, lines_list, 'Coupler', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Coupler(object_ID, lines_list)
        elif type == 'Divisional':
            self.check_attribute_value(object_ID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_ID, lines_list, 'Divisional', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Divisional(object_ID, lines_list)
        elif type == 'DivisionalCoupler':
            self.check_attribute_value(object_ID, lines_list, 'DivisionalCoupler', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_DivisionalCoupler(object_ID, lines_list)
        elif type == 'Enclosure':
            self.check_attribute_value(object_ID, lines_list, 'Enclosure', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Enclosure(object_ID, lines_list)
        elif type == 'General':
            self.check_attribute_value(object_ID, lines_list, 'General', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_General(object_ID, lines_list)
        elif type == 'Label':
            self.check_object_Label(object_ID, lines_list)
        elif type == 'Manual':
            self.check_attribute_value(object_ID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Manual(object_ID, lines_list)
        elif type == 'ReversiblePiston':
            self.check_attribute_value(object_ID, lines_list, 'ReversiblePiston', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_ReversiblePiston(object_ID, lines_list)
        elif type == 'Stop':
            self.check_attribute_value(object_ID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_ID, lines_list, 'Stop', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Stop(object_ID, lines_list)
        elif type == 'Swell':
            self.check_object_Enclosure(object_ID, lines_list)
        elif type == 'Switch':
            self.check_attribute_value(object_ID, lines_list, 'Switch', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Switch(object_ID, lines_list)
        elif type == 'Tremulant':
            self.check_attribute_value(object_ID, lines_list, 'Tremulant', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Tremulant(object_ID, lines_list)
        else:
            self.check_object_SetterElement(object_ID, lines_list, type)

    #-------------------------------------------------------------------------------------------------
    def check_object_PanelOther(self, object_ID, lines_list):
        #--- check the data of an other kind of Panel object section (Panel999Coupler999, Panel999Divisional999, ...) which the lines are in the given lines list

        # get the object type from the object ID (for example Coupler from Panel999Coupler999)
        object_type = object_ID[8:-3]
        object_type_plur = object_ID[8:-3] + 's' if object_type != 'Switch' else object_ID[8:-3] + 'es'

        # check the attributes of the object depending on the object type
        if object_type == 'Coupler':
            self.check_object_Coupler(object_ID, lines_list)
        elif object_type == 'Divisional':
            self.check_object_Divisional(object_ID, lines_list)
        elif object_type == 'DivisionalCoupler':
            self.check_object_DivisionalCoupler(object_ID, lines_list)
        elif object_type == 'Enclosure':
            self.check_object_Enclosure(object_ID, lines_list)
        elif object_type == 'General':
            self.check_object_General(object_ID, lines_list)
        elif object_type == 'Image':
            self.check_object_Image(object_ID, lines_list)
        elif object_type == 'Label':
            self.check_object_Label(object_ID, lines_list)
        elif object_type == 'ReversiblePiston':
            self.check_object_ReversiblePiston(object_ID, lines_list)
        elif object_type == 'SetterElement':
            self.check_object_SetterElement(object_ID, lines_list)
        elif object_type == 'Stop':
            self.check_object_Stop(object_ID, lines_list)
        elif object_type == 'Switch':
            self.check_object_Switch(object_ID, lines_list)
        elif object_type == 'Tremulant':
            self.check_object_Tremulant(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Piston(self, object_ID, lines_list):
        #--- check the data of a Piston object section which the lines are in the given lines list

        # required attributes
        ret = self.check_attribute_value(object_ID, lines_list, 'ObjectType', ATTR_TYPE_PISTON_TYPE, True)
        self.check_attribute_value(object_ID, lines_list, 'ManualNumber', ATTR_TYPE_OBJECT_REF, ret in ('STOP', 'COUPLER'))
        self.check_attribute_value(object_ID, lines_list, 'ObjectNumber', ATTR_TYPE_INTEGER, False, 1, 200)

        # a Piston has also the attributes of a Push Button
        self.check_object_PushButton(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_PushButton(self, object_ID, lines_list):
        #--- check the data of a Push Button object section which the lines are in the given lines list

        # a Push Button has only the attributes of a Button
        self.check_object_Button(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Rank(self, object_ID, lines_list):
        #--- check the data of a Rank object section which the lines are in the given lines list

        is_rank_obj = object_ID.startswith('Rank') # some mandatory attributes are not mandatory for objects which inherit the Rank attributes (like Stop)

        # required attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_ID, lines_list, 'FirstMidiNoteNumber', ATTR_TYPE_INTEGER, is_rank_obj, 0, 256)
        self.check_attribute_value(object_ID, lines_list, 'WindchestGroup', ATTR_TYPE_OBJECT_REF, True)
        self.check_attribute_value(object_ID, lines_list, 'Percussive', ATTR_TYPE_BOOLEAN, True)

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_ID, lines_list, 'Gain', ATTR_TYPE_FLOAT, False, -120, 40)
        self.check_attribute_value(object_ID, lines_list, 'PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_ID, lines_list, 'TrackerDelay', ATTR_TYPE_INTEGER, False, 0, 10000)
        self.check_attribute_value(object_ID, lines_list, 'HarmonicNumber', ATTR_TYPE_FLOAT, False, 1, 1024)
        self.check_attribute_value(object_ID, lines_list, 'PitchCorrection', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_ID, lines_list, 'MinVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_ID, lines_list, 'MaxVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_ID, lines_list, 'AcceptsRetuning', ATTR_TYPE_BOOLEAN, False)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfLogicalPipes', ATTR_TYPE_INTEGER, is_rank_obj, 1, 192)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):  # Pipe999xxx attributes
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}', ATTR_TYPE_PIPE_WAVE, True)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Percussive', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Gain', ATTR_TYPE_FLOAT, False, -120, 40)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}TrackerDelay', ATTR_TYPE_FLOAT, False, 0, 10000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}LoadRelease', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}AttackVelocity', ATTR_TYPE_INTEGER, False, 0, 127)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}MaxTimeSinceLastRelease', ATTR_TYPE_INTEGER, False, -1, 100000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}AttackStart', ATTR_TYPE_INTEGER, False, 0, 158760000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}HarmonicNumber', ATTR_TYPE_FLOAT, False, 1, 1024)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}MIDIKeyNumber', ATTR_TYPE_INTEGER, False, -1, 127)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}PitchCorrection', ATTR_TYPE_FLOAT, False, -1200, 1200)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}AcceptsRetuning', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}WindchestGroup', ATTR_TYPE_OBJECT_REF, False)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}MinVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}MaxVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)

                ret1 = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}LoopCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Loop999xxx attributes
                        ret = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Loop{str(idx1).zfill(3)}Start', ATTR_TYPE_INTEGER, False, 0, 158760000)
                        loop_start = int(ret) if ret.isdigit() else 1
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Loop{str(idx1).zfill(3)}End', ATTR_TYPE_INTEGER, False, loop_start + 1, 158760000)

                ret1 = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}AttackCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Attack999xxx attributes
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}LoadRelease', ATTR_TYPE_BOOLEAN, False)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}AttackVelocity', ATTR_TYPE_INTEGER, False, 0, 127)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}MaxTimeSinceLastRelease', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}AttackStart', ATTR_TYPE_INTEGER, False, 0, 158760000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)

                        ret2 = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}LoopCount', ATTR_TYPE_INTEGER, False, 1, 100)
                        if ret2.isdigit():
                            for idx2 in range(1, int(ret2)+1):  # Pipe999Attack999Loop999xxx attributes
                                ret = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}Loop{str(idx2).zfill(3)}Start', ATTR_TYPE_INTEGER, True, 0, 158760000)
                                loop_start = int(ret) if ret.isdigit() else 1
                                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}Loop{str(idx2).zfill(3)}End', ATTR_TYPE_INTEGER, True, loop_start + 1, 158760000)

                ret1 = self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Release999xxx attributes
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                        self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)

                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}LoopCrossfadeLength', ATTR_TYPE_INTEGER, False, 0, 120)
                self.check_attribute_value(object_ID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseCrossfadeLength', ATTR_TYPE_INTEGER, False, 0, 120)

    #-------------------------------------------------------------------------------------------------
    def check_object_ReversiblePiston(self, object_ID, lines_list):
        #--- check the data of a Reversible Piston object section which the lines are in the given lines list

        # unkown expected attributes...
        pass

     #-------------------------------------------------------------------------------------------------
    def check_object_SetterElement(self, object_ID, lines_list, type = ''):
        #--- check the data of a Setter Element object section which the lines are in the given lines list

        # required attributes
        if type == '':
            # type not provided by the caller, recover it from the object lines list
            type = self.check_attribute_value(object_ID, lines_list, 'Type', ATTR_TYPE_ELEMENT_TYPE, True)

        if type == 'CrescendoLabel':
            self.check_object_Label(object_ID, lines_list)
        elif type in ('CrescendoA', 'CrescendoB', 'CrescendoC', 'CrescendoD'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('CrescendoPrev', 'CrescendoNext', 'CrescendoCurrent'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('Current', 'Full', 'GC'):
            self.check_object_Button(object_ID, lines_list)
        elif type[:7] == "General" and len(type) == 9 and type[7:9].isdigit() and int(type[7:9]) in range(1, 51):
            self.check_object_Button(object_ID, lines_list)
        elif type == 'GeneralLabel':
            self.check_object_Label(object_ID, lines_list)
        elif type in ('GeneralPrev', 'GeneralNext', 'Home', 'Insert', 'Delete'):
            self.check_object_Button(object_ID, lines_list)
        elif type[:1] == "L" and len(type) == 2 and type[1:2].isdigit() and int(type[1:2]) in range(0, 10):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('M100', 'M10', 'M1', 'P1', 'P10', 'P100'):
            self.check_object_Button(object_ID, lines_list)
        elif type == 'PitchLabel':
            self.check_object_Label(object_ID, lines_list)
        elif type in ('PitchM100', 'PitchM10', 'PitchM1', 'PitchP1', 'PitchP10', 'PitchP100'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('Prev', 'Next', 'Set'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('Regular', 'Scope', 'Scoped', 'Save'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('SequencerLabel', 'TemperamentLabel'):
            self.check_object_Label(object_ID, lines_list)
        elif type in ('TemperamentPrev', 'TemperamentNext'):
            self.check_object_Button(object_ID, lines_list)
        elif type in ('TransposeDown', 'TransposeUp'):
            self.check_object_Button(object_ID, lines_list)
        elif type == 'TransposeLabel':
            self.check_object_Label(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Stop(self, object_ID, lines_list):
        #--- check the data of a Stop object section which the lines are in the given lines list

        is_stop_obj = object_ID.startswith('Stop') # some mandatory attributes are not mandatory for objects which inherit the Stop attributes

        # optional attribute
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfRanks', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret == '' or not ret.isdigit():
            # number of ranks not defined or not a number
            nb_ranks = 0
        else:
            nb_ranks = int(ret)

        # required attributes
        self.check_attribute_value(object_ID, lines_list, 'FirstAccessiblePipeLogicalKeyNumber', ATTR_TYPE_INTEGER, is_stop_obj, 1, 128)
        self.check_attribute_value(object_ID, lines_list, 'FirstAccessiblePipeLogicalPipeNumber', ATTR_TYPE_INTEGER, nb_ranks == 0, 1, 192)

        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfAccessiblePipes', ATTR_TYPE_INTEGER, True, 1, 192)
        nb_pipes = int(ret) if ret.isdigit() else 192

        # optional attributes
        if nb_ranks > 0:
            for idx in range(1, nb_ranks+1):
                self.check_attribute_value(object_ID, lines_list, f'Rank{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_ID, lines_list, f'Rank{str(idx).zfill(3)}FirstPipeNumber', ATTR_TYPE_INTEGER, False, 1, nb_pipes)
                self.check_attribute_value(object_ID, lines_list, f'Rank{str(idx).zfill(3)}PipeCount', ATTR_TYPE_INTEGER, False, 0, nb_pipes)
                self.check_attribute_value(object_ID, lines_list, f'Rank{str(idx).zfill(3)}FirstAccessibleKeyNumber', ATTR_TYPE_INTEGER, False, 1, nb_pipes)
        elif nb_ranks == 0:
            # number of ranks set at 0, the Stop must contain rank attributes
            self.check_object_Rank(object_ID, lines_list)

        # a Stop has also the attributes of a Drawstop
        self.check_object_DrawStop(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Switch(self, object_ID, lines_list):
        #--- check the data of a Switch object section which the lines are in the given lines list

        # a Switch has only the attributes of a Drawstop
        self.check_object_DrawStop(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Tremulant(self, object_ID, lines_list):
        #--- check the data of a Tremulant object section which the lines are in the given lines list

        # optional attributes
        ret = self.check_attribute_value(object_ID, lines_list, 'TremulantType', ATTR_TYPE_TREMULANT_TYPE, False)
        is_synth = (ret == 'Synth')
        self.check_attribute_value(object_ID, lines_list, 'Period', ATTR_TYPE_INTEGER, is_synth, 32, 44100)
        self.check_attribute_value(object_ID, lines_list, 'StartRate', ATTR_TYPE_INTEGER, is_synth, 1, 100)
        self.check_attribute_value(object_ID, lines_list, 'StopRate', ATTR_TYPE_INTEGER, is_synth, 1, 100)
        self.check_attribute_value(object_ID, lines_list, 'AmpModDepth', ATTR_TYPE_INTEGER, is_synth, 1, 100)

        # a Tremulant has also the attributes of a Drawstop
        self.check_object_DrawStop(object_ID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_WindchestGroup(self, object_ID, lines_list):
        #--- check the data of a WindChest Group object section which the lines are in the given lines list

        # required attributes
        max = self.objects_type_count('Enclosure')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Enclosure{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_ID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_ID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        self.check_attribute_value(object_ID, lines_list, 'Name', ATTR_TYPE_STRING, False)

    #-------------------------------------------------------------------------------------------------
    def check_attribute_value(self, object_ID, lines_list, attribute_name, attribute_value_type, required_attribute, attribute_value_min=0, attribute_value_max=0):
        #--- check if the given attribute name is present in the given object lines list, and if its value is correct for its value type and min/max values
        #--- the min and max values are ignored if max <= min. The given lines list is considered to be sorted
        #--- returns the value of the attribute if it has been found and without error, else return ''

        # check that the given max value is higher or equal to the min value (this should never happen)
        if attribute_value_max < attribute_value_max:
            self.events_log_add(f"INTERNAL ERROR : check_attribute_value called with max < min for {object_ID} / {attribute_name} : min={attribute_value_min}, max={attribute_value_max}")
            return ''

        # recover the value of the attribute to check
        (attr_value, attr_idx) = self.object_get_attribute_value(lines_list, attribute_name, True)

        if attr_idx != -1:
            # the attribute has been found
            self.check_nb_attr += 1

            line = lines_list[attr_idx]

            # check the attribute value according to the given type

            if attribute_value_type == ATTR_TYPE_INTEGER:
                if (not attr_value.lstrip("-+").isdigit() or
                    ((int(attr_value) < attribute_value_min or int(attr_value) > attribute_value_max))):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value must be an integer in the range [{attribute_value_min} - {attribute_value_max}]")
                    # return an attribute value which is limited to the min or max value, if it is a decimal value
                    attr_value = attr_value.lstrip("-+")
                    if attr_value.isdigit():
                        if int(attr_value) < attribute_value_min:
                            attr_value = str(attribute_value_min)
                        else:
                            attr_value = str(attribute_value_max)
                    else:
                        attr_value = ''

            elif attribute_value_type == ATTR_TYPE_FLOAT:
                if (not(attr_value.lstrip("-+").replace('.', '', 1).isdigit()) or
                    ((float(attr_value) < attribute_value_min or float(attr_value) > attribute_value_max))):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value must be an integer or decimal in the range [{attribute_value_min} - {attribute_value_max}]")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_BOOLEAN:
                if attr_value.upper() not in ('Y', 'N'):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value must be Y or N (boolean attribute)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_STRING:
                pass # nothing to check in case of string value

            elif attribute_value_type == ATTR_TYPE_COLOR:
                if (not(attr_value.upper() in ('BLACK', 'BLUE', 'DARK BLUE', 'GREEN', 'DARK GREEN', 'CYAN', 'DARK CYAN', 'RED', 'DARK RED',
                                               'MAGENTA', 'DARK MAGENTA', 'YELLOW', 'DARK YELLOW', 'LIGHT GREY', 'DARK GREY', 'WHITE', 'BROWN')) and
                    not(len(attr_value) == 7 and attr_value[0] == '#' and attr_value[1:].isdigit())):  # check of the HTML format #RRGGBB
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid color (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_FONT_SIZE:
                if (not(attr_value.upper() in ('SMALL', 'NORMAL', 'LARGE')) and
                    not(attr_value.isdigit() and int(attr_value) >= 1 and int(attr_value) <= 50)):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid font size (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_PANEL_SIZE:
                if (not(attr_value.upper() in ('SMALL', 'MEDIUM', 'MEDIUM LARGE', 'LARGE')) and
                    not(attr_value.isdigit() and int(attr_value) >= 100 and int(attr_value) <= 4000)):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid panel size (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_OBJECT_REF:  # for example Switch002=12 or ManualNumber=2 or Stop003Manual=2 or Pipe015WindchestGroup=1
                if attribute_name[-3:].isdigit():
                    attribute_name = attribute_name[:-3]   # remove the three digits at the end of the attribute name to get the object name

                if attribute_name[-6:] == 'Number':
                    attribute_name = attribute_name[:-6]   # remove the 'Number' string at the end, used in General and Piston objects
                elif attribute_name[-6:] == 'Manual':
                    attribute_name = 'Manual'         # keep only the 'Manual' string, used in General object
                elif attribute_name[-14:] == 'WindchestGroup':
                    attribute_name = 'WindchestGroup' # keep only the 'WindchestGroup' string, used in Rank object

                attr_value = attr_value.lstrip("+-") # remove possible + or - at the beginning of the value, used in General or Divisional objects

                if not(attribute_name + attr_value.zfill(3)) in self.odf_objects_dict:
                    self.events_log_add(f"Error in {object_ID} / {line} : the object {attribute_name + attr_value.zfill(3)} does not exist")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_ELEMENT_TYPE:
                if (not(attr_value in ('Coupler', 'Divisional', 'DivisionalCoupler', 'Enclosure', 'General', 'Label', 'Manual', 'ReversiblePiston', 'Stop', 'Swell',
                                      'Switch', 'Tremulant', 'CrescendoA', 'CrescendoB', 'CrescendoC', 'CrescendoD', 'CrescendoPrev', 'CrescendoNext', 'CrescendoCurrent',
                                      'Current', 'Full', 'GC', 'GeneralLabel', 'GeneralPrev', 'GeneralNext', 'Home', 'Insert', 'Delete', 'M100', 'M10', 'M1', 'P1', 'P10', 'P100',
                                      'PitchLabel', 'PitchP1', 'PitchP10', 'PitchP100', 'PitchM1', 'PitchM10', 'PitchM100', 'Prev', 'Next', 'Set', 'Regular', 'Scope', 'Scoped',
                                      'Save', 'SequencerLabel', 'TemperamentLabel', 'TemperamentPrev', 'TemperamentNext', 'TransposeDown', 'TransposeUp', 'TransposeLabel')) and
                    not(attr_value[0] == 'L' and attr_value[1].isdigit() and int(attr_value[1]) in range(0, 10)) and
                    not(attr_value[:14] == 'CrescendoLabel' and attr_value[14:].isdigit() and int(attr_value[14:]) in range(1, 33)) and
                    not(attr_value[:7] == 'General' and attr_value[7:].isdigit() and int(attr_value[7:]) in range(1, 51))):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid panel element type (look at the help)")
                    attr_value = ''
                pass

            elif attribute_value_type == ATTR_TYPE_COUPLER_TYPE:
                if not(attr_value.upper() in ('NORMAL', 'BASS', 'MELODY')):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid coupler type (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_TREMULANT_TYPE:
                if not(attr_value.upper() in ('SYNTH', 'WAVE')):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid tremulant type (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_PISTON_TYPE:
                if not(attr_value.upper() in ('STOP', 'COUPLER', 'SWITCH', 'TREMULANT')):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid piston type (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_DRAWSTOP_FCT:
                if not(attr_value.upper() in ('INPUT', 'NOT', 'AND', 'XOR', 'NAND', 'NOR', 'OR')):
                    self.events_log_add(f"Error in {object_ID} / {line} : the assigned value is not a valid drawstop function (look at the help)")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_FILE_NAME:
                modif_path = attr_value.replace('\\', '/')
                if self.check_files_names and not os.path.isfile(os.path.dirname(self.odf_file_name) + '/' + modif_path):
                    self.events_log_add(f"Error in {object_ID} / {line} : file does not exist")
                    attr_value = ''

            elif attribute_value_type == ATTR_TYPE_PIPE_WAVE:
                if attr_value.upper()[-4:] == '.WAV':
                    modif_path = attr_value.replace('\\', '/')
                    if self.check_files_names and not os.path.isfile(os.path.dirname(self.odf_file_name) + '/' + modif_path):
                        self.events_log_add(f"Error in {object_ID} / {line} : file not found")
                        attr_value = ''
                elif attr_value[:4] == 'REF:':  # for example REF:001:005:007
                    if not (attr_value[5:7].isdigit and attr_value[7] == ':' and
                            attr_value[8:11].isdigit and attr_value[11] == ':' and
                            attr_value[12:15].isdigit and len(attr_value) == 15):
                        self.events_log_add(f"Error in {object_ID} / {line} : wrong pipe referencing, expected REF:999:999:999")
                        attr_value = ''
                elif attr_value != 'EMPTY':
                    self.events_log_add(f"Error in {object_ID} / {line} : wrong pipe definition")
                    attr_value = ''

             # remove the line of the found attribute, to know at the end of the object check which of its attributes have not been checked
            lines_list.pop(attr_idx)

        elif required_attribute:
            # the attribute has not been found and it is required
            self.events_log_add(f"Error in {object_ID} : the attribute {attribute_name} is expected, it is missing or misspelled")

        return attr_value

    #-------------------------------------------------------------------------------------------------
    def check_attributes_unicity(self, object_ID, lines_list):
        #--- check in the given object lines list if each attribute is unique

        # copy the attributes names of the given lines list in an attributes list
        attributes_list = []
        for line in lines_list:
            if self.is_line_with_attribute(line):
                (attr_name, attr_value) = line.split("=", 1)
                attributes_list.append(attr_name)

        # sort the attributes list
        attributes_list.sort()

        # check if there are consecutive names in the sorted list
        for i in range(0, len(attributes_list) - 1):
            if attributes_list[i] == attributes_list[i+1]:
                self.events_log_add(f"Error in {object_ID} : the attribute {attributes_list[i]} is defined more than once")

#-------------------------------------------------------------------------------------------------
class C_GUI():
    #--- class to manage the graphical user interface of the application

    odf_data = None             # one instance of the C_ODF class
    selected_object_ID = ''     # ID of the object currently selected in the objects list or tree widgets
    data_changed = False        # flag indicating that data have been changed in the odf_data and not saved in an ODF
    object_edited = False       # flag indicating that the data of an object have been edited (and not yet applied in odf_data)s
    gui_events_blocked = False  # flag indicating that the GUI events are currently blocked
    text_in_search = ''         # text which is currently in search in the help
    search_index = ''           # last search result position in the help

    tag_field = "tag_field"     # tag to identify the syntax color for the fields
    tag_comment = "tag_comment" # tag to identify the syntax color for the comments
    tag_obj_ID = "tag_obj_ID"   # tag to identify the syntax color for the object IDs
    tag_title = "tag_title"     # tag to identify the syntax color for the titles in the help
    tag_found = "tag_found"     # tag to identify the syntax color for the string found by the search in the help

    #-------------------------------------------------------------------------------------------------
    def wnd_main_build(self):
        #--- build the main window of the application with all his GUI widgets

        #--- create an instance of the C_ODF class
        self.odf_data = C_ODF()

        #--- create the main window
        self.wnd_main = Tk(className='OdfEdit')
        self.wnd_main.title(MAIN_WINDOW_TITLE)
        self.wnd_main.geometry('1600x800')
        self.wnd_main.bind('<Configure>', self.wnd_main_configure) # to adjust the widgets size on main windows resizing
        self.wnd_main.protocol("WM_DELETE_WINDOW", self.wnd_main_quit) # to ask the user to save his changed before to close the main window
        # assign an image to the main window icon
        icon = PhotoImage(file = os.path.dirname(__file__) + '/OdfEdit_res/OdfEdit.png')
        self.wnd_main.iconphoto(False, icon)

        #--- define the styles of some widgets
        ttk.Style().theme_use('clam')
        ttk.Style().configure("Treeview", highlightthickness=3, font=('Calibri', 11), foreground="black")
        ttk.Style().configure("TNotebook.Tab", font=('Calibri', 11), foreground="black")
        self.wnd_main.option_add("*TCombobox*Listbox*Background", 'white')
        self.wnd_main.option_add("*TCombobox*Listbox*Foreground", 'black')

        #--- create the various widgets inside the main window

        # button "New"
        self.btn_odf_new = Button(self.wnd_main, text="New", fg="black", command=self.file_new)
        self.btn_odf_new.place(x=10, y=10, width=70, height=20)

        # button "Open"
        self.btn_odf_file_open = Button(self.wnd_main, text="Open", fg="black", command=self.file_open)
        self.btn_odf_file_open.place(x=90, y=10, width=70, height=20)

        # button "Save"
        self.btn_odf_file_save = Button(self.wnd_main, text="Save", fg="black", state=DISABLED, command=self.file_save)
        self.btn_odf_file_save.place(x=170, y=10, width=80, height=20)

        # button "Save as..."
        self.btn_odf_file_saveas = Button(self.wnd_main, text="Save as...", fg="black", state=DISABLED, command=self.file_saveas)
        self.btn_odf_file_saveas.place(x=260, y=10, width=80, height=20)

        # button "Quit"
        self.btn_quit_appli = Button(self.wnd_main, text="Quit", fg="black", command=self.wnd_main_quit)
        self.btn_quit_appli.place(x=960, y=10, width=70, height=20)

        # button "Apply changes"
        self.btn_object_apply_chg = Button(self.wnd_main, text="Apply changes", fg="black", state=DISABLED, command=self.object_text_apply_chg)
        self.btn_object_apply_chg.place(x=530, y=45, width=100, height=20)
        CreateToolTip(self.btn_object_apply_chg, "Apply the changes dones in the text box below in the selected object or create a new object if the object ID is different.")

        # button "Delete"
        self.btn_object_delete = Button(self.wnd_main, text="Delete", fg="black", state=DISABLED, command=self.object_text_delete)
        self.btn_object_delete.place(x=640, y=45, width=100, height=20)
        CreateToolTip(self.btn_object_delete, "Delete the selected object.")

        # button "Do checks"
        self.btn_data_check = Button(self.wnd_main, text="Do checks", fg="black", state=DISABLED, command=self.check_odf_lines)
        self.btn_data_check.place(x=790, y=45, width=100, height=20)
        CreateToolTip(self.btn_data_check, "Execute checks in the loaded ODF data (syntax, compliance with the specification).")

        # button "Show in help"
        self.btn_show_help = Button(self.wnd_main, text="Show in help", fg="black", state=DISABLED, command=self.help_selected_object)
        self.btn_show_help.place(x=930, y=45, width=100, height=20)
        CreateToolTip(self.btn_show_help, "Show in the help tab the part describing the selected object.")

        # button "Collapse all" for the objects tree
        self.btn_collapse_all = Button(self.wnd_main, text="Collapse all", fg="black", state=DISABLED, command=self.objects_tree_collapse_all)
        self.btn_collapse_all.place(x=310, y=45, width=80, height=20)

        # button "Expand all" for the objects tree
        self.btn_expand_all = Button(self.wnd_main, text="Expand all", fg="black", state=DISABLED, command=self.objects_tree_expand_all)
        self.btn_expand_all.place(x=400, y=45, width=80, height=20)

        # label with loaded ODF file name
        self.lab_odf_file_name = Label(self.wnd_main, text="", fg="black", borderwidth=1, relief="solid", anchor=W)
        self.lab_odf_file_name.place(x=350, y=10, width=600, height=20)

        # label with the number of objects in the objects list
        self.lab_objects_nb = Label(self.wnd_main, text="", fg="black", borderwidth=0, relief="solid", anchor=CENTER)
        self.lab_objects_nb.place(x=10, y=50, width=250, height=20)

        # label with the number and list of parents of the selected object ID
        self.lab_parents_list = Label(self.wnd_main, text="", fg="black", borderwidth=0, relief="solid", anchor=NW, wraplength=500)
        self.lab_parents_list.place(x=530, y=70, width=500, height=30)

        # list box with objects IDs and names, with horizontal and vertical scroll bars
        # a frame is used to encapsulate the list box and scroll bars to facilitate their resizing
        self.frm_object_list = Frame(self.wnd_main)
        self.frm_object_list.place(x=10, y=70, width=250, height=520)
        scrollbarv = ttk.Scrollbar(self.frm_object_list, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh = ttk.Scrollbar(self.frm_object_list, orient='horizontal')
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.lst_objects_list = Listbox(self.frm_object_list, bg='white', font='Calibri 11', fg="black", exportselection=0, selectmode='single', activestyle='none')
        self.lst_objects_list.pack(side=LEFT, fill=BOTH, expand=True)
        self.lst_objects_list.bind('<<ListboxSelect>>', self.objects_list_selected)
        self.lst_objects_list.config(yscrollcommand=scrollbarv.set)
        self.lst_objects_list.config(xscrollcommand=scrollbarh.set)
        scrollbarv.config(command=self.lst_objects_list.yview)
        scrollbarh.config(command=self.lst_objects_list.xview)

        # treeview to display the objects hierarchy, with horizontal and vertical scroll bars
        # a frame is used to encapsulate the tree box and scroll bar to facilitate their resizing
        self.frm_object_tree = Frame(self.wnd_main)
        self.frm_object_tree.place(x=270, y=70, width=250, height=520)
        scrollbarv = ttk.Scrollbar(self.frm_object_tree, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh = ttk.Scrollbar(self.frm_object_tree, orient='horizontal')
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.trv_objects_tree = ttk.Treeview(self.frm_object_tree, show="tree", selectmode='browse') #, style="myTVstyle.Treeview")
        self.trv_objects_tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.trv_objects_tree.column('#0', width=500)
        self.trv_objects_tree.bind('<<TreeviewSelect>>', self.objects_tree_selected)
        self.trv_objects_tree.config(yscrollcommand=scrollbarv.set)
        self.trv_objects_tree.config(xscrollcommand=scrollbarh.set)
        scrollbarv.config(command=self.trv_objects_tree.yview)
        scrollbarh.config(command=self.trv_objects_tree.xview)

        # text box to edit the data of an object, with vertical and horizontal scroll bars
        # a frame is used to encapsulate the text box and scroll bars
        self.frm_object_text = Frame(self.wnd_main)
        self.frm_object_text.place(x=530, y=100, width=500, height=490)
        scrollbarv = ttk.Scrollbar(self.frm_object_text, orient='vertical')
        scrollbarh = ttk.Scrollbar(self.frm_object_text, orient='horizontal')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.txt_object_text = Text(self.frm_object_text, fg="black", bg='white', bd=3, wrap="none", font="Calibri 11", selectbackground="snow3", undo=True)
        self.txt_object_text.pack(side=LEFT, fill=BOTH, expand=True)
        self.txt_object_text.bind('<<Modified>>', self.object_text_changed)
        self.txt_object_text.bind('<KeyRelease>', self.object_text_key_pressed)
        self.txt_object_text.config(xscrollcommand=scrollbarh.set, yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_object_text.yview)
        scrollbarh.config(command=self.txt_object_text.xview)
        # create a context menu
        self.txt_object_text.bind("<Button-3>", self.object_text_context_menu)
        self.obj_txt_menu = Menu(self.txt_object_text, tearoff=0)
        self.obj_txt_menu.add_command(label="Clear all", command=self.object_text_clear)
        # define the tags for the syntax highlighting
        self.txt_object_text.tag_config(self.tag_field, foreground='red3')
        self.txt_object_text.tag_config(self.tag_comment, foreground='chartreuse4')
        self.txt_object_text.tag_config(self.tag_obj_ID, foreground='blue2', font='Calibri 11 bold')

        # notebook to display the events logs or the help
        self.notebook = ttk.Notebook(self.wnd_main)
        self.notebook.place(x=1040, y=10, width=550, height=580)

        # text box to display the application events logs in the notebook, with horizontal/vertical scroll bars
        # a frame is used to encapsulate the text box and scroll bars
        self.frm_logs = Frame(self.notebook)
        self.frm_logs.pack(fill=BOTH, expand=True)
        scrollbarv = ttk.Scrollbar(self.frm_logs, orient='vertical')
        scrollbarh = ttk.Scrollbar(self.frm_logs, orient='horizontal')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.txt_events_log = Text(self.frm_logs, fg="black", bg='ivory2', bd=3, wrap="none", font='Calibri 11', selectbackground="grey")
        self.txt_events_log.pack(side=LEFT, fill=BOTH, expand=True)
        self.txt_events_log.config(xscrollcommand=scrollbarh.set, yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_events_log.yview)
        scrollbarh.config(command=self.txt_events_log.xview)
        # create a context menu
        self.txt_events_log.bind("<Button-3>", self.events_log_text_context_menu)
        self.logs_txt_menu = Menu(self.txt_events_log, tearoff=0)
        self.logs_txt_menu.add_command(label="Clear all", command=self.events_log_text_clear)

        # text box to display the help in the notebook, with vertical scroll bar and search widgets
        # a main frame is used to encapsulate two other frames, one for the search widgets, one for the text box and his scroll bar
        self.frm_help = Frame(self.notebook)
        self.frm_help.pack(fill=BOTH, expand=True)
        # widgets to search a text
        self.frm_help_search = Frame(self.frm_help)
        self.frm_help_search.place(x=0, y=0, height=30, relwidth=1.0)
        self.lab_search = Label(self.frm_help_search, text="Search :", fg="black", borderwidth=0, relief="solid", anchor=E)
        self.lab_search.place(x=10, y=5, width=60, height=20)
        self.cmb_search_text = ttk.Combobox(self.frm_help_search, height=24, values=['[Organ]', '[Button]', '[Coupler999]', '[Divisional999]', '[DivisionalCoupler999]', '[DrawStop]', '[Enclosure999]', '[General999]', '[Image999]', '[Label999]', '[Manual999]', '[Panel999]', '[Panel999Element999]', '[Panel999Image999]', '[Panel999xxxxx999]', '[Piston]', '[PushButton]', '[Rank999]', '[ReversiblePiston999]', '[SetterElement999]', '[Stop999]', '[Switch999]', '[Tremulant999]', '[WindchestGroup999]'])
        self.cmb_search_text.place(x=80, y=5, width=170, height=20)
        self.cmb_search_text.bind('<KeyRelease>', self.help_search_text_key_pressed)
        self.cmb_search_text.bind('<<ComboboxSelected>>', self.help_search_text_key_pressed)
        self.btn_search_prev = Button(self.frm_help_search, text="<", fg="black", state=NORMAL, command=self.help_search_previous)
        self.btn_search_prev.place(x=260, y=5, width=40, height=20)
        self.btn_search_next = Button(self.frm_help_search, text=">", fg="black", state=NORMAL, command=self.help_search_next)
        self.btn_search_next.place(x=310, y=5, width=40, height=20)
        self.btn_search_clear = Button(self.frm_help_search, text="Clear", fg="black", state=NORMAL, command=self.help_search_clear)
        self.btn_search_clear.place(x=360, y=5, width=80, height=20)
        self.lab_search_occur_nb = Label(self.frm_help_search, text="", fg="black", borderwidth=0, relief="solid", anchor=W)
        self.lab_search_occur_nb.place(x=450, y=5, width=100, height=20)
        # help text box
        self.frm_help_text = Frame(self.frm_help)
        self.frm_help_text.place(x=0, y=30, height=300, relwidth=1.0)
        scrollbarv = ttk.Scrollbar(self.frm_help_text, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        self.txt_help = Text(self.frm_help_text, fg="black", bg='azure', bd=3, wrap="word", font='Calibri 11', selectbackground="grey")
        self.txt_help.pack(side=BOTTOM, fill=BOTH, expand=True)
        self.txt_help.config(yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_help.yview)
        # define the tags for the syntax highlighting
        self.txt_help.tag_config(self.tag_field, foreground='red3')
        self.txt_help.tag_config(self.tag_comment, foreground='chartreuse4')
        self.txt_help.tag_config(self.tag_obj_ID, foreground='blue2', font='Calibri 11 bold')
        self.txt_help.tag_config(self.tag_title, foreground='red3', font='Calibri 11 bold')

        # list to search in the ODF and display the search results
        # a main frame is used to encapsulate two other frames, one for the search widgets, one for the list box and his scroll bar
        self.frm_search = Frame(self.notebook)
        self.frm_search.pack(fill=BOTH, expand=True)
        # widgets to search a text
        self.frm_odf_search = Frame(self.frm_search)
        self.frm_odf_search.place(x=0, y=0, height=30, relwidth=1.0)
        self.ent_odf_search_text = Entry(self.frm_odf_search)
        self.ent_odf_search_text.place(x=20, y=5, width=170, height=20)
        self.btn_odf_search = Button(self.frm_odf_search, text="Search", fg="black", state=NORMAL, command=self.odf_sresults_search)
        self.btn_odf_search.place(x=200, y=5, width=80, height=20)
        # search results list box
        self.frm_odf_sresults = Frame(self.frm_search)
        self.frm_odf_sresults.place(x=0, y=30, height=300, relwidth=1.0)
        scrollbarv = ttk.Scrollbar(self.frm_odf_sresults, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        self.lst_odf_sresults = Listbox(self.frm_odf_sresults, bg='light yellow', font='Calibri 11', fg="black", exportselection=0, selectmode='single', activestyle='none')
        self.lst_odf_sresults.pack(side=LEFT, fill=BOTH, expand=True)
        self.lst_odf_sresults.bind('<Double-1>', self.odf_sresults_list_selected)
        self.lst_odf_sresults.config(yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.lst_odf_sresults.yview)

        # create the notebook tabs, and attach the frames to them
        self.notebook.add(self.frm_logs, text="    Logs    ")
        self.notebook.add(self.frm_help, text="    Help    ")
        self.notebook.add(self.frm_search, text="    Search in ODF    ")

        self.wnd_main.geometry('1600x800') # to trigger the call to wnd_main_configure to resize the widgets
        self.gui_status_do_update()

        # launch a timer to execute 200ms after the application init some time consuming activities
        self.wnd_main.after(200, self.do_boot_loadings)

        return self.wnd_main

    #-------------------------------------------------------------------------------------------------
    def wnd_main_configure(self, event):
        #--- (GUI event callback) the main window configuration has changed

        if str(event.widget) == '.':
            # configure event of the main window
            # resize some widgets so that they fit the size of the main window
            self.frm_object_list.place(height=int(event.height) - self.frm_object_list.winfo_y() - 10)
            self.frm_object_tree.place(height=int(event.height) - self.frm_object_tree.winfo_y() - 10)
            self.frm_object_text.place(height=int(event.height) - self.frm_object_text.winfo_y() - 10)
            self.notebook.place(width=int(event.width) - self.notebook.winfo_x() - 10, height=int(event.height) - self.notebook.winfo_y() - 10)
            self.frm_help_text.place(height=int(event.height) - self.frm_help_text.winfo_y() - 50)
            self.frm_odf_sresults.place(height=int(event.height) - self.frm_odf_sresults.winfo_y() - 50)

    #-------------------------------------------------------------------------------------------------
    def wnd_main_quit(self):
        #--- (GUI event callback) the user has clicked on the button "Quit" or window top-right "X"

        if self.save_modif_before_change(True, True):
            # the user has saved his modifications if he wanted and has not canceled the operation
            self.wnd_main.destroy()

    #-------------------------------------------------------------------------------------------------
    def do_boot_loadings(self):
        #--- function to execute CPU time consuming loading operations just after the boot of the application
        #--- in order to not slowdown the application GUI appearance time

        # load an ODF (for debug only)
##        file_name = "D:/fichiers/Python/OdfEdit/ODF_examples/demo.organ"
##        file_name = "D:\\fichiers\\Python\\OdfEdit\\ODF_examples\\Giubiasco.organ"
##        file_name = "D:/GrandOrgue/SampleSet Demo/demo.organ"
##        if self.odf_data.odf_lines_load(file_name):
##            # the file has been loaded properly
##            # update the objects list and tree
##            self.selected_object_ID = ''
##            self.objects_list_tree_do_update()
##            self.gui_status_do_update()
##        self.events_log_text_display()

        # load the help text
        self.help_text_load()

    #-------------------------------------------------------------------------------------------------
    def file_new(self):
        #--- (GUI event callback) the user has clicked on the button "New"
        #--- do a reset of the objects list/tree, edit box and ODF data

        if self.save_modif_before_change(file_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            self.selected_object_ID = ''
            # clear the object text box
            self.object_text_do_update()
            # clear the objects list
            self.lst_objects_list.delete(0, END)
            # clear the objects tree
            for item in self.trv_objects_tree.get_children():
                self.trv_objects_tree.delete(item)
            # clear the ODF data
            self.odf_data.odf_reset_all_data()

            self.data_changed = False
            # update the status of some GUI widgets
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def file_open(self):
        #--- (GUI event callback) the user has clicked on the button "Open"

        if self.save_modif_before_change(file_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            # let the user select the ODF file to open
            file_name = fd.askopenfilename(title='Open ODF', filetypes=[('ODF', '*.organ')])
            if file_name != '':
                # a file has been selected by the user
                if self.odf_data.odf_lines_load(file_name):
                    # the file has been loaded properly
                    # update the objects list / tree / text
                    self.initial_dir = file_name
                    self.selected_object_ID = ''
                    self.objects_list_tree_do_update()
                    self.object_text_do_update()

                    self.data_changed = False
                else:
                    # error in loading the file, reset all
                    self.file_new()

                self.gui_status_do_update()
                self.events_log_text_display()

                # select the logs tab of the notebook to show the opening logs
                self.notebook.select(self.frm_logs)

    #-------------------------------------------------------------------------------------------------
    def file_save(self):
        #---  (GUI event callback) the user has clicked on the button "Save"

        if self.odf_data.odf_file_name == '':
            # no file name known, do a 'save as' operation
            self.file_saveas()
        elif self.odf_data.odf_lines_save(''):
            # the ODF data have been correctly saved in the loaded ODF file
            self.data_changed = False
            self.gui_status_do_update()
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def file_saveas(self):
        #---  (GUI event callback) the user has clicked on the button "Save as"

        # let the user select the ODF file to which make the save
        file_name = fd.asksaveasfilename(title='Save in ODF...', filetypes=[('ODF', '*.organ')])

        if file_name != '':
            # a file has been selected by the user
            if self.odf_data.odf_lines_save(file_name):
                # the ODF data have been correctly saved
                self.data_changed = False
                self.gui_status_do_update()
            self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def save_modif_before_change(self, file_change=False, object_change=False):
        #--- before a file change (file_change=True) or a selected object change (object_change=True) or a window closing
        #--- ask to the user if he wants to save his modifications if any, if the answer is yes then do it
        #--- return True if the user has not answered Cancel

        operation_not_canceled = True

        if (file_change or object_change) and self.object_edited:
            # the coming change is at file or object level and an object content has been edited
            # ask to the user if he wants to apply the changed object data
            confirm = messagebox.askyesnocancel(title="Data changed", message="Do you want to apply the changed object data ?")
            if confirm:  # answer is yes
                self.object_text_apply_chg()
            elif confirm is None:  # answer is cancel
                operation_not_canceled = False
            else:  # answer is no
                pass

        if file_change and self.data_changed and operation_not_canceled:
            # the coming change is at file level and the ODF data have been changed (and the operation has not been yet canceled just before)
            # ask to the user if he wants to save the changed ODF data
            confirm = messagebox.askyesnocancel(title="Data changed", message="Do you want to save the modified ODF data ?")
            if confirm:  # answer is yes
                self.file_save()
            elif confirm is None:  # answer is cancel
                operation_not_canceled = False
            else:  # answer is no
                pass

        return operation_not_canceled

    #-------------------------------------------------------------------------------------------------
    def gui_events_block(self):
        #--- set the flag which blocks the GUI events processing
        #--- returns True if the events are already blocked, else False (in case of False the caller can process its GUI event)
        #--- this permits to avoid the application to react to all the GUI events caused by changes that ifself is making in widgets
        #--- which causes several bad side effects in the widgets behavior and final status

        if self.gui_events_blocked == False:
            # the events are not yet blocked
            self.gui_events_blocked = True
            # launch a timer which will unblock the events 200ms later
            self.wnd_main.after(200, self.gui_events_unblock)
            return False
        else:
            return True

    #-------------------------------------------------------------------------------------------------
    def gui_events_unblock(self):
        #--- (GUI event callback) end of a timer started by the function gui_events_block
        #--- reset the flag which blocks the GUI events processing

        self.gui_events_blocked = False

    #-------------------------------------------------------------------------------------------------
    def gui_status_do_update(self):
        #--- update the status of some GUI widgets in a single time, according to some status of the application

##        print('\ngui_status_do_update, selected object is ' + self.selected_object_ID)
##        print('   call stack : ' + inspect.stack()[1].function + ' / ' + inspect.stack()[2].function + ' / ' + inspect.stack()[3].function)

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        objects_nb = len(self.odf_data.odf_objects_dict)

        # button "Save"
        self.btn_odf_file_save['state'] = NORMAL if (self.odf_data.odf_file_name != '' and self.data_changed) else DISABLED
        self.btn_odf_file_save['foreground'] = 'red' if (self.odf_data.odf_file_name != '' and self.data_changed) else 'grey'

        # button "Save as"
        self.btn_odf_file_saveas['state'] = NORMAL if objects_nb > 0 else DISABLED

        # button "Apply changes"
        self.btn_object_apply_chg['state'] = NORMAL if self.object_edited else DISABLED
        self.btn_object_apply_chg['foreground'] = 'red' if self.object_edited else 'grey'

        # button "Delete"
        self.btn_object_delete['state'] = NORMAL if (self.selected_object_ID != '' and self.selected_object_ID != 'Header') else DISABLED

        # button "Do check"
        self.btn_data_check['state'] = NORMAL if objects_nb > 0 else DISABLED

        # button "Show help"
        self.btn_show_help['state'] = NORMAL if self.selected_object_ID != '' else DISABLED

        # buttons "Collapse all" and "Expand all"
        self.btn_collapse_all['state'] = NORMAL if objects_nb > 0 else DISABLED
        self.btn_expand_all['state'] = NORMAL if objects_nb > 0 else DISABLED

        # buttons to search previous or next or clear the search in the help
        is_search_text = (self.cmb_search_text.get() != '')
        self.btn_search_prev['state'] = NORMAL if is_search_text else DISABLED
        self.btn_search_next['state'] = NORMAL if is_search_text else DISABLED
        self.btn_search_clear['state'] = NORMAL if is_search_text else DISABLED

        # label with the loaded ODF name
        if self.odf_data.odf_file_name == '':
            if objects_nb == 0:
                self.lab_odf_file_name.config(text='Click on the button "Open" to load an ODF')
            else:
                self.lab_odf_file_name.config(text='Click on the button "Save as" to define a file name')
        else:
            self.lab_odf_file_name.config(text=self.odf_data.odf_file_name)

        # label with the number of objects
        if objects_nb == 0:
            self.lab_objects_nb.config(text="None object")
        elif objects_nb == 1:
            self.lab_objects_nb.config(text="1 object")
        else:
            self.lab_objects_nb.config(text=str(objects_nb) + " objects")

        if objects_nb > 0:
            # objects list : select the item corresponding to the selected object ID
            self.lst_objects_list.selection_clear(0, 'end')
            for i in range(0, self.lst_objects_list.size()):
                if self.lst_objects_list.get(i).split(' ')[0] == self.selected_object_ID:
                    self.lst_objects_list.selection_set(i)
                    self.lst_objects_list.see(i)
                    break;

            # objects tree : select the items corresponding to the selected object ID
            # unselect the root of the objects tree if it was selected
            self.trv_objects_tree.selection_remove('0')
            for iid in self.trv_objects_tree.get_children('0'):
                self.__objects_tree_select_nodes(iid, self.selected_object_ID)

    #-------------------------------------------------------------------------------------------------
    def objects_list_selected(self, event):
        #--- (GUI event callback) the user has selected an item in the objects list widget
        #--- select the same object ID in the objects list widget, and show the object ID content in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        # get the selected indice
        selected_indice = self.lst_objects_list.curselection()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            if selected_indice != ():
                # an item of the objects list widget is selected
                # recover in the objects list widget the object ID of the selected item (before the opening parenthesis)
                self.selected_object_ID = self.lst_objects_list.get(selected_indice[0]).split(' (')[0]

                # update the object text box
                self.object_text_do_update()
                # update the status of GUI widgets
                self.gui_status_do_update()

##                print(f'\n{self.selected_object_ID} selected')
##                print(f'parents : {self.odf_data.odf_objects_dict[self.selected_object_ID][IDX_OBJ_PAR]}')
##                print(f'children : {self.odf_data.odf_objects_dict[self.selected_object_ID][IDX_OBJ_CHI]}')
##                print(f'parent panel : {self.odf_data.object_get_parent_panel_ID(self.selected_object_ID)}')

    #-------------------------------------------------------------------------------------------------
    def objects_list_tree_do_update(self):
        #--- do an update the objects list and objects tree widgets

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # update the objects list widgets
        self.lst_objects_list.delete(0, END)
        for dict_key, dict_value in self.odf_data.odf_objects_dict.items():
            self.lst_objects_list.insert(END, dict_key + " (" + dict_value[IDX_OBJ_NAME] + ")")

        # update the objects tree widget
        # delete all the nodes of the tree
        for item in self.trv_objects_tree.get_children():
            self.trv_objects_tree.delete(item)
        if len(self.odf_data.odf_objects_dict):
            # add the root node
            self.node_id = 0
            root_object_ID = "Header"
            parent_node_id = str(self.node_id)
            self.trv_objects_tree.insert('', 0, str(self.node_id), text=root_object_ID, open=True)
            # add in the tree the children of the objects which have no parent (i.e. which the parent is the Root)
            # inside the called function all the children will be added recursively
            for dict_key, dict_value in self.odf_data.odf_objects_dict.items():
                if len(dict_value[IDX_OBJ_PAR]) == 0:
                    # the object has no parents
                    self.__objects_tree_add_child(parent_node_id, dict_key)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_selected(self, event):
        #--- (GUI event callback) the user has selected an item in the objects tree widget
        #--- select the same object ID in the objects tree widget, and show the object ID content in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        # get the indice of the selected item
        selected_indice = self.trv_objects_tree.focus()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            # recover the object ID
            self.selected_object_ID = self.trv_objects_tree.item(selected_indice, option='text').split(' (')[0]

            # update the object text box
            self.object_text_do_update()
            # update the status of GUI widgets
            self.gui_status_do_update()

            # make the selected item visibile if it is no more visible after the execution of gui_status_do_update due to some upper nodes opening
            if self.trv_objects_tree.bbox(selected_indice) == '':
                self.trv_objects_tree.see(selected_indice)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_expand_all(self):
        #--- (GUI event callback) the user has pressed the button "Expand all"
        # expend all the nodes of the objects tree widget

        self.trv_objects_tree.item('0', open=True)
        for iid in self.trv_objects_tree.get_children('0'):
            self.__objects_tree_open_node_and_children(iid, True)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_collapse_all(self):
        #--- (GUI event callback) the user has pressed the button "Collapse all"
        # collapse all the nodes of the objects tree widget except the root and the 'Organ' nodes

        self.trv_objects_tree.item('0', open=True)
        for iid in self.trv_objects_tree.get_children('0'):
            self.__objects_tree_open_node_and_children(iid, False)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_open_node_and_children(self, node_iid, open_status):
        #--- recursive function to open (if True, else close) the given node and his children in the objects tree

        if self.trv_objects_tree.item(node_iid, option='text') == 'Organ':
            # the Organ node must stay always opened
            self.trv_objects_tree.item(node_iid, open=True)
        else:
            self.trv_objects_tree.item(node_iid, open=open_status)

        # apply the open status to the children nodes
        for iid in self.trv_objects_tree.get_children(node_iid):
            self.__objects_tree_open_node_and_children(iid, open_status)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_open_node_and_parents(self, node_iid):
        #--- recursive function to open the given node and his parents in the objects tree

        if node_iid != '0':
            self.trv_objects_tree.item(node_iid, open=True)

            # apply the open status to the children nodes
            self.__objects_tree_open_node_and_parents(self.trv_objects_tree.parent(node_iid))

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_select_nodes(self, node_iid, object_ID):
        #--- recursive function to select the nodes of the objects tree which contain the given object ID

        if self.trv_objects_tree.item(node_iid)['text'].split(' (')[0] == object_ID:
            # the node node_iid corresponds to the object ID : select it
            self.trv_objects_tree.selection_add(node_iid)
            # open the parents of the node
            self.__objects_tree_open_node_and_parents(self.trv_objects_tree.parent(node_iid))
        else:
            self.trv_objects_tree.selection_remove(node_iid)

        # do the operation for the children of node_iid
        for iid in self.trv_objects_tree.get_children(node_iid):
            self.__objects_tree_select_nodes(iid, object_ID)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_add_child(self, parent_node_id, child_object_ID):
        #--- recursive function to add in the objects tree widget the given child linked to the given parent

        # add in the tree a node for the given child under the given parent
        self.node_id += 1
        # recover the name of the object ID in the dictionnary
        obj_name = self.odf_data.odf_objects_dict.get(child_object_ID)[IDX_OBJ_NAME]
        if child_object_ID == "Organ":
            # for the Organ object, open the tree node in addition to add the child
            self.trv_objects_tree.insert(parent_node_id, 'end', str(self.node_id), text=child_object_ID, open=True)
        else:
            self.trv_objects_tree.insert(parent_node_id, 'end', str(self.node_id), text=child_object_ID + ' (' + obj_name + ')')
        if child_object_ID == self.selected_object_ID:
            # the added object ID corresponds to the selected object ID, then select it and show it
            self.trv_objects_tree.selection_add(str(self.node_id))
            self.trv_objects_tree.see(str(self.node_id))

        # the child becomes the parent for the next recursive call
        new_parent_node_id = str(self.node_id)
        new_parent_ID = child_object_ID

        # parse the children of new parent to add the corresponding children nodes
        if new_parent_ID in self.odf_data.odf_objects_dict:
            # the new parent object ID is actually present in the dictionnary
            children_list = self.odf_data.odf_objects_dict[new_parent_ID][IDX_OBJ_CHI]
            if len(children_list) > 0:
                for child_ID in children_list:
                    self.__objects_tree_add_child(new_parent_node_id, child_ID)
        else:
            pass  # do nothing if the object ID is not found in the dictionnary

    #-------------------------------------------------------------------------------------------------
    def object_text_do_update(self):
        # -- update the content of the object text box widget

        # get the list of the selected object ID data
        object_list = self.odf_data.object_get_data_list(self.selected_object_ID)

        # write the object data in the object text box
        self.txt_object_text.delete(1.0, "end")
        self.txt_object_text.insert(1.0, '\n'.join(object_list))

        # update object the parents list label
        self.object_text_do_parents_update()

        # highlight the syntax of the object data
        self.odf_syntax_highlight(self.txt_object_text)

        # reset the text modified flag
        self.txt_object_text.edit_modified(False)
        self.object_edited = False

    #-------------------------------------------------------------------------------------------------
    def object_text_do_parents_update(self):
        #--- update the parents list label

        if self.selected_object_ID in ('', 'Header'):
            # no object ID selected or header selected : none parent to display
            self.lab_parents_list.config(text='')
        else:
            try:
                # recover the number of parents for the selected object ID
                nb_parents = len(self.odf_data.odf_objects_dict[self.selected_object_ID][IDX_OBJ_PAR])
            except:
                # object not found in the dictionnary
                self.lab_parents_list.config(text="Undefined object")
            else:
                if nb_parents == 0:
                    self.lab_parents_list.config(text="")
                elif nb_parents == 1:
                    self.lab_parents_list.config(text=f"{self.selected_object_ID} linked with {' '.join(self.odf_data.odf_objects_dict[self.selected_object_ID][IDX_OBJ_PAR])}")
                elif nb_parents >= 1:
                    self.lab_parents_list.config(text=f"{self.selected_object_ID} linked with {nb_parents} objects : {' '.join(self.odf_data.odf_objects_dict[self.selected_object_ID][IDX_OBJ_PAR])}")

    #-------------------------------------------------------------------------------------------------
    def object_text_changed(self, event):
        #--- (GUI event callback) the user has made a change in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        if self.txt_object_text.edit_modified() and self.object_edited == False:
            # update the status of GUI widgets
            self.object_edited = True
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def object_text_apply_chg(self):
        #--- (GUI event callback) the user has clicked on the button "Apply changes"
        #--- apply the content of the object text widget in the ODF data

        # convert the object text lines in list elements
        object_list = self.txt_object_text.get(1.0, "end").splitlines()

        # apply the object data in the ODF data
        ret = self.odf_data.object_set_data_list(self.selected_object_ID, object_list)
        if ret != '':
            # the modification has been applied
            self.data_changed = True
            # recover the object ID of the applied text
            self.selected_object_ID = ret
            # update the objects list and tree
            self.objects_list_tree_do_update()
            # update object the parents list label
            self.object_text_do_parents_update()

            # reset the edit modified flag
            self.txt_object_text.edit_modified(False)
            self.object_edited = False

            # update the status of GUI widgets
            self.gui_status_do_update()

        # update the events log text
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def object_text_delete(self):
        #--- (GUI event callback) the user has clicked on the button "Delete" to delete the current selected object ID

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # remove the object in the ODF data
        if self.odf_data.object_remove(self.selected_object_ID):
            # the object has been removed
            # clear the current object ID
            self.selected_object_ID = ''
            # update the objects list and tree
            self.objects_list_tree_do_update()
            # update the object text
            self.object_text_do_update()

            # update the status of GUI widgets
            self.data_changed = True
            self.gui_status_do_update()

        # update the events log text
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def object_text_context_menu(self, event):
        #--- (GUI event callback) the user has made a right click in the object text box : open the context menu

        try:
            self.obj_txt_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.obj_txt_menu.grab_release()

    #-------------------------------------------------------------------------------------------------
    def object_text_clear(self):
        #--- (GUI event callback) the user has selected 'Clear all' in the context menu of the object text box

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # clear the current object ID
        self.selected_object_ID = ''

        # update the object text
        self.object_text_do_update()

        # reset the edit modified flag
        self.txt_object_text.edit_modified(False)
        self.object_edited = False
        self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def object_text_key_pressed(self, event):
        #--- (GUI event callback) the user has pressed a keyboard key in the object text box

        # update the syntax highlighting
        self.odf_syntax_highlight(self.txt_object_text)

    #-------------------------------------------------------------------------------------------------
    def odf_sresults_search(self):
        #--- (GUI event callback) the user has clicked on the button search of the ODF search results tab

        # recover the text to search
        search_text = self.ent_odf_search_text.get()

        if search_text != '':
            object_ID = 'Header'
            results_list = []
            for line in self.odf_data.odf_lines_list:

                if self.odf_data.is_line_with_object_ID(line): # line with an object ID
                    object_ID = line[1:-1] # remove the brackets in first and last characters to get the object ID

                if search_text in line:
                    results_list.append(f'{object_ID} : {line}')

            results_list.sort()

            self.lst_odf_sresults.delete(0, END)
            self.lst_odf_sresults.insert(END, *results_list)

    #-------------------------------------------------------------------------------------------------
    def odf_sresults_list_selected(self, event):
        #--- (GUI event callback) the user has clicked on an item of the ODF search results list

        # get the selected indice
        selected_indice = self.lst_odf_sresults.curselection()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            self.selected_object_ID = self.lst_odf_sresults.get(selected_indice[0]).split(' :')[0]

            # update the object text box
            self.object_text_do_update()
            # update the status of GUI widgets
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_context_menu(self, event):
        #--- (GUI event callback) the user has made a right click in the logs text box : open the context menu

        try:
            self.logs_txt_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.logs_txt_menu.grab_release()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_display(self):
        #--- add in the events log text box widget the content of the events log buffer then clear it

        self.txt_events_log.insert('end', '\n' + '\n'.join(self.odf_data.events_log_list) + '\n')
        self.txt_events_log.see('end-1c linestart')  # to see the start of the last line of the text
        self.txt_events_log.update_idletasks() # to force a refresh of the text box

        # reset the events log buffer
        self.odf_data.events_log_clear()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_clear(self):
        #--- (GUI event callback) the user has selected 'Clear all' in the context menu of the logs text box

        # clear the content of the logs text box
        self.txt_events_log.delete(1.0, "end")

        # reset the events log buffer
        self.odf_data.events_log_clear()

    #-------------------------------------------------------------------------------------------------
    def help_text_load(self):
        #--- load in the help text box widget the help for the user
        #--- done one time at the application start

        # copy in the widget the help text
        self.txt_help.insert(1.0, HELP_TEXT)
        # apply the ODF syntax highlighting
        self.odf_syntax_highlight(self.txt_help)
        # disable the text box to not permit its editing
        self.txt_help.configure(state='disabled')

    #-------------------------------------------------------------------------------------------------
    def help_selected_object(self):
        #--- (GUI event callback) the user has clicked on the button "Show in help"
        #--- search and display in the help the part mentioning the selected object help

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        if self.selected_object_ID not in ["", "Header"]:
            #substitute the digits by the char 9 in the object ID to create a generic object ID
            gen_object_ID = '['
            for c in self.selected_object_ID: gen_object_ID += '9' if c.isdigit() else c
            gen_object_ID += ']'

            # put the generic object ID in the search text widget
            self.cmb_search_text.delete(0, END)
            self.cmb_search_text.insert(0, gen_object_ID)

            # update the status of some GUI widgets
            self.gui_status_do_update()

            # search the first occurence of the generic object ID
            self.help_search_next()

            # select the Help tab of the notebook
            self.notebook.select(self.frm_help)

    #-------------------------------------------------------------------------------------------------
    def help_search_next(self):
        #--- (GUI event callback) the user has clicked on the button '>'
        #--- show the next occurence of the text to search

        self.help_search_text(self.cmb_search_text.get(), True)

    #-------------------------------------------------------------------------------------------------
    def help_search_previous(self):
        #--- (GUI event callback) the user has clicked on the button '<'
        #--- show the previous occurence of the text to search

        self.help_search_text(self.cmb_search_text.get(), False)

    #-------------------------------------------------------------------------------------------------
    def help_search_clear(self):
        #--- (GUI event callback) the user has clicked on the button 'Clear'
        #--- clear the text to search (text box and highlighting)

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        self.cmb_search_text.delete(0, END)
        self.help_search_text('', False)
        self.lab_search_occur_nb.config(text='')

        # update the status of some GUI widgets
        self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def help_search_text(self, text_to_find, search_next = True):
        # show in the help the next occurence (or previous if search_next=False) of the given text to find
        # highlight in yellow all the occurences of this text

        text_len = len(text_to_find)

        if self.text_in_search != text_to_find:
            # a new text has to be searched, highlight all its occurences in the entire help text

            # remove the highlight of the previous searched text occurences
            self.txt_help.tag_remove(self.tag_found, '1.0', END)
            nb_occurences = 0

            # store the new text to search
            self.text_in_search = text_to_find

            if text_to_find != '':
                # highlight the occurences of the text to find in the entire help
                self.txt_help.tag_config(self.tag_found, foreground='black', background='yellow', font='Calibri 11')
                # get the lines of the text widget
                lines = self.txt_help.get('1.0', END).splitlines()
                # parse all the lines
                for l in range(0, len(lines)):
                    idx = 0
                    while idx != -1:
                        # check the various occurences of the searched text in the current line (if any)
                        idx = lines[l].find(text_to_find, idx)
                        if idx != -1:
                            # highlight the found occurence in the line
                            self.txt_help.tag_add(self.tag_found, f'{l+1}.{idx}', f'{l+1}.{idx} + {text_len} chars')
                            # move the search index after the found occurence
                            idx += text_len
                            nb_occurences += 1

                # display the number of occurences of the searched text
                self.lab_search_occur_nb.config(text=f'{nb_occurences} occurences')

        if self.text_in_search != '':
            # search for the text in the widget
            if search_next and self.search_index != '':
                # if search upward, move the current search position after the previous found position
                self.search_index = f'{self.search_index} + {text_len} chars'

            # search for the next/previous occurence
            if self.search_index == '': self.search_index = '1.0'
            self.search_index = self.txt_help.search(self.text_in_search, self.search_index, backwards = not (search_next))

            if self.search_index != '':
                # show the found text
                self.txt_help.see(self.search_index)
            else:
                messagebox.showinfo(title="Search result", message=f"{self.text_in_search} is not found")

    #-------------------------------------------------------------------------------------------------
    def help_search_text_key_pressed(self, event):
        #--- (GUI event callback) the user has pressed a keyboard key in the text search in help

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # remove the selection which appear automatically on the text when an item is selected in a combobox
        self.cmb_search_text.selection_clear()

        # update the status of some GUI widgets
        self.gui_status_do_update()

        if event.keysym == 'Return' and self.cmb_search_text.get() != '':
            self.help_search_next()

    #-------------------------------------------------------------------------------------------------
    images_ref=[]  # list needed to keep in memory the reference to the images opened by PhotoImage and added in the text box, else they are not displayed (Python bug ?)

    def odf_syntax_highlight(self, txt_widget):
        #--- apply syntax highlighting to the content of the given object text box widget

        # remove the tags previously set in the text box
        txt_widget.tag_remove(self.tag_field, '1.0', END)
        txt_widget.tag_remove(self.tag_comment, '1.0', END)
        txt_widget.tag_remove(self.tag_obj_ID, '1.0', END)
        txt_widget.tag_remove(self.tag_title, '1.0', END)

        # put in a list the lines of the text box
        lines = txt_widget.get('1.0', END).splitlines()

        # parse all the characters of the text box lines
        for l in range(0, len(lines)):
            for c in range(0, len(lines[l])):
                if lines[l][0] == ';':  # comment line
                    txt_widget.tag_add(self.tag_comment, f'{l+1}.0', f'{l+1}.0 lineend')
                    break
                elif lines[l][0] == '[' and lines[l][c] == ']':  # object ID
                    txt_widget.tag_add(self.tag_obj_ID, f'{l+1}.0', f'{l+1}.{c+1}')
                    break
                elif txt_widget.get(f'{l + 1}.{c}') == '=':  # equal char in a attribute=value line
                    txt_widget.tag_add(self.tag_field, f'{l+1}.0', f'{l + 1}.{c}')
                    break
                elif lines[l][:2] == '§§' :  # image file name to insert (in the help)
                    # recover the file name after the '§§' tag
                    file_name = lines[l][2:]
                    # remove the file name in the widget
                    txt_widget.delete(f'{l+1}.0', f'{l+1}.0 lineend')
                    try:
                        # open the image file
                        photo = PhotoImage(file = os.path.dirname(__file__) + '/' + file_name)
                        # add the reference of the image in the list to store these references
                        self.images_ref.append(photo)
                        # insert the image in the text box
                        txt_widget.image_create(f'{l+1}.0', image=photo, padx=10, pady=10)
                    except:
                        # insert a message indicating that the image has not been opened
                        txt_widget.insert(f'{l+1}.0', f'!!! cannot open the image {file_name}')
                    break
                elif lines[l][:2] == '>>' :  # title line (in the help)
                    txt_widget.delete(f'{l+1}.0', f'{l+1}.3')
                    txt_widget.tag_add(self.tag_title, f'{l+1}.0', f'{l+1}.0 lineend')
                    break

    #-------------------------------------------------------------------------------------------------
    def check_odf_lines(self):
        #--- check the consistency of the ODF data

        # ask to the user to apply his object data change before to launch the check
        if self.save_modif_before_change(object_change=True):
            # the user has not cancelled the operation

            self.odf_data.events_log_add("Checking the data...")
            self.events_log_text_display()

            # do the check
            self.odf_data.check_odf_lines(self.check_odf_lines_status_update)

            # update the events log text
            self.events_log_text_display()

            # select the Logs tab of the notebook to show the check result
            self.notebook.select(self.frm_logs)

            # restore the object parents label content
            self.object_text_do_parents_update()

    #-------------------------------------------------------------------------------------------------
    def check_odf_lines_status_update(self, object_ID):
        #--- callback function called by the C_ODF.check_odf_lines function to display in the parents label widget the object ID currently checked

        self.lab_parents_list.config(text=f"Checking {object_ID}...")
        self.lab_parents_list.update_idletasks()

#-------------------------------------------------------------------------------------------------
class CreateToolTip(object):
    # class to create a tooltip for a given widget
    # tk_ToolTip_class101.py
    # gives a Tkinter widget a tooltip as the mouse is above the widget
    # tested with Python27 and Python34  by  vegaseat  09sep2014
    # www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter
    # Modified to include a delay time by Victor Zaccardo, 25mar16
    # example of usage : tooltip = CreateToolTip(parend_widget, "string to display")
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None
    def enter(self, event=None):
        self.schedule()
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)
    def unschedule(self):
        id = self.id
        self.id = None
        if id: self.widget.after_cancel(id)
    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify='left',
        background="#ffffff", relief='solid', borderwidth=1,
        wraplength = self.wraplength)
        label.pack(ipadx=1)
    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw: tw.destroy()


#-------------------------------------------------------------------------------------------------
def main():
    #--- main function of the application

    # initiate a C_GUI class instance, display the main window based on this instance, start the main loop of this window
    C_GUI().wnd_main_build().mainloop()

#-------------------------------------------------------------------------------------------------
# help displayed in the tab "Help" of the application

HELP_TEXT = """
>> General information
This tool is intended to help in editing and checking an organ definition file (ODF, extension .organ) in plain text mode.
To completely check the goodness of an ODF, load it in GrandOrgue who will detect deeply all the remaining errors if any.
Right-click on the object edition or logs text areas to open a contextual menu permitting to clear all the text in the area.
The help below is largely inspired and copy/pasted from the GrandOrgue help.

An ODF is a text file in ISO-8859-1 encoding. The standard extension is .organ. As an alternative, the file might be encoded in UTF-8 if it starts with the appropriate byte order marker.
It is composed of several object sections, each one being organized like this :
[Object ID]
; comment line anywhere
attribute1=value1
attribute2=value2

Comment lines are started with ; in the first column.
Empty lines are ignored.
The text is case sensitive for object ID and attributes.
Each object ID (also called section name) must occur once in the ODF.
Each attribute (also called setting) must occur once in his object section.


>> Objects ID summary

Available objects IDs (999 stands for a 3-digits placeholder, it must be higher than 0, it can be equal to 0 for Manual and Panel only) :
[Organ] the general description of the instrument (and the main panel for old panel format)
[Coupler999] the means to apply key press of a manual to key of another manual
[Divisional999] a combinaisons memory applied at manual level
[DivisionalCoupler999] the means to apply divisional selection of a manual to divisional of another manual
[Enclosure999] a swell pedal which has effect on a wind-chest
[General999] a combinaisons memory applied at organ level
[Manual999] a manual or a pedal
[Panel999] a window containing graphical user interface (GUI) elements
[Panel999Image999] an image to display in a panel (additional panel if old panel format)
[Rank999] a group of pipes with similar sonic properties
[Stop999] the means to activate a selection of ranks
[Switch999] the means to toggle the state of couplers / stops / tremulants
[Tremulant999] the means to apply a tremulant effect to a wind-chest
[WindchestGroup999] a wind-chest on which ranks of pipes are placed

GUI objects ID used with the NEW panel format only :
[Panel999Element999] an element (switch, stop, manual, label, general, setter, ...)

GUI objects ID used with the OLD panel format only :
in the main panel :
[Image999] an image
[Label999] a label
[ReversiblePiston999] a piston which toggles between on and off at each push
[SetterElement999] an element to show/change a setting
in additional panels :
[Panel999Coupler999] a coupler
[Panel999Divisional999] a divisional
[Panel999DivisionalCoupler999] a divisional coupler
[Panel999Enclosure999] an enclosure
[Panel999General999] a general
[Panel999Label999] a label
[Panel999ReversiblePiston999] a reversible piston
[Panel999SetterElement999] a setter element
[Panel999Stop999] a stop
[Panel999Switch999] a switch
[Panel999Tremulant999] a tremulant

The NEW panel format is characterized by the presence of a Panel000 object (the main panel) which contains the attribute NumberOfGUIElements.
With the OLD panel format, the main panel is defined inside the Organ object (no Panel000 object to define).

Each object can consist of a backend part representing the object, and its configuration (eg. list of sample file names) and multiple GUI representations.
Objects like stops only displayed on a non-main panel need an invisible definition for the backend part on the main panel too.

Objects which define the number of other objects are :
[Organ]
NumberOfDivisionalCouplers -> [DivisionalCoupler999]
NumberOfEnclosures -> [Enclosure999]
NumberOfGenerals -> [General999]
NumberOfManuals -> [Manual999]
NumberOfPanels -> [Panel999]
NumberOfRanks -> [Rank999]
NumberOfSwitches ->	[Switch999]
NumberOfTremulants -> [Tremulant999]
NumberOfWindchestGroups -> [WindchestGroup999]
Old panel format (for the main panel) :
    NumberOfImages -> [Image999]
    NumberOfLabels -> [Label999]
    NumberOfReversiblePistons -> [ReversiblePiston999]
    NumberOfSetterElements -> [SetterElement999]

[Manual999]
NumberOfCouplers -> [Coupler999]
NumberOfDivisionals -> [Divisional999]
NumberOfStops -> [Stop999]

[Panel999]
New panel format :
    NumberOfGUIElements -> [Panel999Element999]
New and old panel formats :
    NumberOfImages -> [Panel999Image999]
Old panel format :
    NumberOfCouplers ->	[Panel999Coupler999]
    NumberOfDivisionals -> [Panel999Divisional999]
    NumberOfDivisionalCouplers -> [Panel999DivisionalCoupler999]
    NumberOfEnclosures -> [Panel999Enclosure999]
    NumberOfGenerals -> [Panel999General999]
    NumberOfLabels -> [Panel999Label999]
    NumberOfReversiblePistons -> [Panel999ReversiblePiston999]
    NumberOfSetterElements -> [Panel999SetterElement999]
    NumberOfStops -> [Panel999Stop999]
    NumberOfSwitches -> [Panel999Switch999]
    NumberOfTremulants -> [Panel999Tremulant999]

The structure of ODF objects hierarchy is (new panel format) :
    Organ
            General...
            Manual...
                    Coupler...
                            Switch...
                    Divisional...
                    DivisionalCoupler...
                    Stop...
                            Rank...
                            Switch...
                    Switch...
                    Tremulant...
                            Switch...
            Panel...
                    Panel...Element...
                            Switch...
                    Panel...Image...
            WindchestGroup...
                    Enclosure...
                    Rank...
                    Stop...
                            Switch...
                    Tremulant...
                            Switch...

Minimum mandatory objects to define in an ODF are :
    Organ
            Manual001
                    Stop001
            Panel000 (new panel format)
            WindchestGroup001
                    Stop001


>> Attributes value types

Boolean : Y for "true", N for "false"

Color : BLACK, BLUE, DARK BLUE, GREEN, DARK GREEN, CYAN, DARK CYAN, RED, DARK RED, MAGENTA, DARK MAGENTA, YELLOW, DARK YELLOW, LIGHT GREY, DARK GREY, WHITE, BROWN. Or HTML syntax #RRGGBB

Font size : SMALL, NORMAL, LARGE or an integer number between 1 and 50

Panel size : SMALL, MEDIUM, MEDIUM LARGE, LARGE or an integer number between 100 and 4000

Image format : bmp, gif, jpg, ico, png

Floating point numbers : -?[0-9]+(.[0-9]*)? means optional minus sign, followed by at least one digit. The decimal separator is a point.

"samples" counts : number of samples from the start of the WAV ﬁle. One sample includes the values of all channels, eg: for a stereo WAV ﬁle at 44.1 kHz, 1 second is equivalent to 44100 samples.

File paths are relative to the location of the ODF. The directory separator must be \ and not contain /. The paths should be considered case sensitive.


>> Objects sections and their attributes

[Organ]
This object describes the whole organ.
For the old panel format, it includes the main panel, therefore the section includes all display metrics attributes.
The new panel format separates the display metrics of the main panel into an object named Panel000.

REQUIRED ATTRIBUTES :
ChurchName=(string, required) Name of the organ/church. This string should be unique, as setting ﬁles for organs with the same ChurchName are considered compatible. GrandOrgue will not load a settings ﬁle if the ChurchName does not match.
ChurchAddress=(string, required) informational text displayed in the property dialog.
HasPedals=(boolean, required) Determines if the pedal, which is deﬁned as section Manual000, is present.

NumberOfDivisionalCouplers=(integer 0-8, required) number of divisional couplers. The details are in a section called DivisionalCoupler999.
NumberOfEnclosures=(integer 0-50, required) number of enclosures. The details of each enclosure are contained in a section called Enclosure999.
NumberOfGenerals=(integer 0-99, required) number of generals. The details are in a section called General999.
NumberOfManuals=(integer 1-16, required) number of manuals. It does not include the pedal keyboard. The manual information for each manual is available in sections called Manual999. 999 is a number deﬁning each manual, starting with 001.
NumberOfPanels=(integer 0-100, required) number of panels in addition to the  main panel. The details are in a section called Panel999.
NumberOfReversiblePistons=(integer 0-32, required) number of reversible pistons. The details of each reversible piston are in a section called ReversiblePiston999.
NumberOfTremulants=(integer 0-10, required) number of tremulants. The details of each tremulant are contained in a section called Tremulant999.
NumberOfWindchestGroups=(integer 1-50, required) number of windchests. The details of each windchest are in a section called WindchestGroup999.

DivisionalsStoreIntermanualCouplers=(boolean, required) determines if divisionals store/change the state of associated intermanual couplers.
DivisionalsStoreIntramanualCouplers=(boolean, required) determines if divisionals store/change the state of associated intramanual couplers.
DivisionalsStoreTremulants=(boolean, required) determines if divisionals store/change the state of associated tremulants.
GeneralsStoreDivisionalCouplers=(boolean, required) determines if divisionals store/change the state of divisional couplers.

OPTIONAL ATTRIBUTES :
OrganBuilder=(string, not required) informational text displayed in the property dialog.
OrganBuildDate=(string, not required) informational text displayed in the property dialog.
OrganComments=(string, not required) informational text displayed in the property dialog.
RecordingDetails=(string, not required) informational text displayed in the property dialog.
InfoFilename=(string, not required) relative path to an html ﬁle with more information about the organ. This setting is currently NOT supported for organ packages.

NumberOfImages=(integer 0-999, default: 0) Number of images on the panel. The section of the label GUI deﬁnitions are called Image999. This setting is NOT supported for the new panel format.
NumberOfLabels=(integer 0-999, default: 0) Number of labels on the panel. The section for each label GUI deﬁnition is called Label999. This setting is NOT supported for the new panel format.
NumberOfRanks=(integer 0-999, default: 0) number of ranks. The details are in a section called Rank999.
NumberOfSetterElements=(integer 0-999, default: 0) Number of setter elements on the panel. The section of the GUI deﬁnitions are called SetterElement999. This setting is NOT supported for the new panel format.
NumberOfSwitches=(integer 0-999, default: 0) number of switches. The details are in a section called Switch999.

CombinationsStoreNonDisplayedDrawstops=(boolean, default: true) determines, if the state of invisible objects (on the main panel) is stored in divisionals, generals and the setter.
AmplitudeLevel=(ﬂoat 0-1000, default: 100) Linear amplitude scale factor applied to the whole organ. 100 means no change.
Gain=(ﬂoat -120 - 40, default: 0) Amplitude scale factor in dB applied to the whole organ. 0 means no change.
PitchTuning=(ﬂoat -1200-1200, default: 0) Retune the whole organ the speciﬁed number of cents.
TrackerDelay=(integer 0 - 10000, default: 0) Delay introduced by the tracker applied to the whole organ.

+ display metrics attributes of a panel if old panel format, see [Panel999]


[Button]
Button object is included inside a drawstop, setter element or push button object. These objects share the following common attributes.

REQUIRED ATTRIBUTES :
None

OPTIONAL ATTRIBUTES :
Name=(string, required) Name of the object. The name may be presented to the user in lists too, therefore it should be descriptive. If a GUI representation requires a shorter name, please override this value locally.
ShortcutKey=(integer 0-255, default: 0) 0 means no shortcut, else it speciﬁes the key code of the shortcut key (see the shortcuts list in the GrandOrgue help).
StopControlMIDIKeyNumber=(integer 0-127, default: no MIDI event speciﬁed) Only used for building the initial conﬁguration during the ﬁrst load - provided just for HW1 compatibility. DEPRECATED.
MIDIProgramChangeNumber=(integer 1-128, default: no MIDI event speciﬁed) Only used for building the initial conﬁguration during the ﬁrst load - provided just for HW1 compatibility. DEPRECATED.

Displayed=(boolean, default: false) If true, the section also includes the GUI attributes for the main panel. Otherwise it is not displayed on the main panel.
DisplayInInvertedState=(boolean, default: false) If true, off is displayed as on and on as off.
DisplayAsPiston=(boolean, default: true for divisionals, generals and pistons, else false) True means to display as piston, false as drawstop
DispLabelColour=(color, default: Dark Red) Color for the label text.
DispLabelFontSize=(font size, default: normal) Size of the label font.
DispLabelFontName=(string, default: empty) Font for the text. Empty means use the control label font of the panel.
DispLabelText=(string, default: Name of the button) Content of the text label. You should edit it, if you need to display a shorter string on the label.
DispKeyLabelOnLeft=(boolean, default: true) If displayed as a piston and this attribute is false, move it a little bit left. Otherwise ignored.
DispImageNum=(integer, type dependent, default: see after) Builtin bitmap set to use. GrandOrgue has 6 for drawstops and 5 for pistons (see image below). The default is 3 (piston) or 4 (drawstops) for read-only buttons, otherwise the default is 1.
§§OdfEdit_res/ImageNumButton.png
DispButtonRow=(button row starting from 0, default: 1) If displayed as piston, it contains the button row according to the layout model. Otherwise ignored.
DispButtonCol=(button column starting from 1, default: 1) If displayed as piston, it contains the button column according to the layout model. Otherwise ignored.
DispDrawstopRow=(drawstop row, default: 1) If displayed as drawstop, it contains the drawstop row according to the layout model. Otherwise ignored.
DispDrawstopCol=(drawstop column, default: 1) If displayed as drawstop, it contains the drawstop column according to the layout model. Otherwise ignored.

ImageOn=(string, default: use internal bitmap according to DispImageNum) Specify the ﬁle name of an image to use as on bitmap. If the bitmap contains a mask for transparency, it will be used.
ImageOff=(string, default: use internal bitmap according to DispImageNum) Specify the ﬁle name of an image to use as off bitmap. If the bitmap contains a mask for transparency, it will be used. The size must match the on bitmap.
MaskOn=(string, default: empty) File name for a external mask for the on bitmap. If empty, no mask is added.
MaskOff=(string, default: value of MaskOn) File name for a external mask for the off bitmap. If empty, no mask is added.

PositionX=(integer 0 - panel width, default: according to layout model) Allow to override X position for button.
PositionY=(integer 0 - panel height, default: according to layout model) Allow to override Y position for button.
Width=(integer 0 - panel width, default: bitmap width) Width of the button. If larger than the bitmap, the bitmap is tiled.
Height=(integer 0 - panel height, default: bitmap height) Height of the button. If larger than the bitmap, the bitmap is tiled.
TileOffsetX=(integer 0 - bitmap width, default: 0) X position on the bitmap of the left pixel of the button.
TileOffsetY=(integer 0 - bitmap height, default: 0) Y position on the bitmap of the top pixel of the button.

MouseRectLeft=(integer 0 - Width, default: 0) relative X of left border of the mouse rectangle.
MouseRectTop=(integer 0 - Height, default: 0) relative Y of top border of the mouse rectangle.
MouseRectWidth=(integer 0 - Width, default: Width) width of the mouse rectangle.
MouseRectHeight=(integer 0 - Height, default: Width) height of the mouse rectangle.
MouseRadius=(integer 0 - max(MouseRectHeight, MouseRectWidth), default: max(MouseRectHeight, MouseRectWidth) / 2). If 0, the mouse events are captured inside the mouse rectangle. Otherwise they must be inside a circle of the speciﬁed size too.

TextRectLeft=(integer 0 - Width, default: 0) relative X of left border of the text rectangle.
TextRectTop=(integer 0 - Height, default: 0) relative Y of top border of the text rectangle.
TextRectWidth=(integer 0 - Width, default: bitmap width) width of the text rectangle.
TextRectHeight=(integer 0 - Height, default: Height) height of the text rectangle.
TextBreakWidth=(integer 0 - TextRectWidth, default: slightly smaller than TextRectWidth) If 0, no text is displayed. Otherwise the value speciﬁes the maximum line length used for text breaking.

Inside the button, the on/off bitmap (depending on the button state) is tiled. If a text width is set, a text label is displayed on it. Mouse events are only captured inside the mouse rectangle.


[Coupler999]
Coupler is a drawstop object with the following additional attributes. It forwards key presses from one manual to other manuals/keys.

REQUIRED ATTRIBUTES :
UnisonOff=(boolean, required) If true, this coupler decouples the manual from the stops (turn it into a ﬂoating manual).
DestinationManual=(integer manual number, required if not a unison off coupler) manual to forward key presses to.
DestinationKeyshift=(integer -24 - 24, required if not a unison off coupler) speciﬁes the keyboard shift between source and destination manual in terms of absolute MIDI note numbers

CoupleToSubsequentUnisonIntermanualCouplers=(boolean, required if not a unison off/melody/bass coupler) Triggers further inter-manual coupler with a destination key shift of zero.
CoupleToSubsequentUpwardIntermanualCouplers=(boolean, required if not a unison off/melody/bass coupler) Triggers further inter-manual coupler with a destination key shift greater than zero.
CoupleToSubsequentDownwardIntermanualCouplers=(boolean, required if not a unison off/melody/bass coupler) Trigger further inter-manual coupler with a destination key shift less than zero.
CoupleToSubsequentUpwardIntramanualCouplers=(boolean, required if not a unison off/melody/bass coupler) Triggers further intra-manual coupler with a destination key shift greater than zero.
CoupleToSubsequentDownwardIntramanualCouplers=(boolean, required if not a unison off/melody/bass coupler) Triggers further intra-manual coupler with a destination key shift less than zero.

OPTIONAL ATTRIBUTES :
CouplerType=(enumeration, default: Normal) Type of the coupler: Normal, Bass or Melody.
FirstMIDINoteNumber=(integer 0-127, default: 0) ﬁrst MIDI note number to forward.
NumberOfKeys=(integer 0-127, default: 0) number of keys to forward starting with FirstMIDINoteNumber.

+ attributes of a drawstop, see [DrawStop]


[Divisional999]
Divisional is a push button object with the following additional attributes.

REQUIRED ATTRIBUTES :
NumberOfCouplers=(integer 0 - coupler count of the manual, required) Number of coupler states stored in this combination. The entries are called Coupler999.
NumberOfStops=(integer 0 - stop count of the manual, required) Number of stop states stored in this combination. The entries are called Stop999.
NumberOfTremulants=(integer 0 - tremulant count of the manual, required) Number of tremulant states stored in this combination. The entries are called Tremulant999.

Coupler999=(integer -999 - 999, required) Number of the coupler. If the value is negative, it is turned off, else turned on.
Stop999=(integer -manual stop count - manual stop count, required) Number of the stop. If the value is negative, it is turned off, else turned on.
Switch999=(integer -manual switch count - manual switch count, required) Number of the switch. If the value is negative, it is turned off, else it is turned on.
Tremulant999=(integer -manual tremulant count - manual tremulant count, required) Number of the tremulant. If the value is negative, it is turned off, else it is turned on.

OPTIONAL ATTRIBUTES :
Protected=(boolean, default: false) If true, the stored combination cannot be changed.
NumberOfSwitches=(integer 0 - switch count of the manual, default) Number of switch states stored in this combination. The entries are called Switch999.

+ attributes of a push button, see [PushButton]


[DivisionalCoupler999]
Divisional coupler is a drawstop object with the following additional attributes. If enabled, activating a divisional on one controlled manual will activate the corresponding divisional on all other manuals.

REQUIRED ATTRIBUTES :
BiDirectionalCoupling=(boolean, required) If false, the coupler only couples upward in the manual list of the coupler, else upward and downward.

NumberOfManuals=(integer 1 - manual count, required) Number of manuals affected by this coupler. The list entries are stored in Manual999 setting.
Manual999=(integer manual number, required) Manual affected by the coupler

+ attributes of a drawstop, see [DrawStop]


[DrawStop]
Drawstop is a button with toogle functions used for coupler, divisional coupler, stop, switch or tremulant, with the following additional non-GUI attributes.

REQUIRED ATTRIBUTES :
Switch999=(integer 1 - switch count, required) Lists the input switches of the logical function of the drawstop. If the drawstop is a switch, it can only reference switches with a lower number. The number of this settings depends on the function.

OPTIONAL ATTRIBUTES :
Function=(enumeration, default: Input) Logical function of the drawstop. If the value is Input, it is a normal user controllable drawstop and has no input switches. Not has one only input and negates the state of the input switch. And, Xor, Nand, Nor as well as Or has a variable number of inputs.
SwitchCount=(integer 1 - switch count, default: 0) Contains the number of input ports, if the logical function allows a variable number number of input. Switch999 contains the referenced switches.
DefaultToEngaged=(boolean, default: False) State of the button after loading.
GCState=(integer -1 - 1, default: implementation deﬁned) State of the button after pressing GC. -1 means no change, 0 off and 1 on.
StoreInDivisional=(boolean, default: dependent on various settings) Determines, if the button should be stored in divisionals without FULL.
StoreInGeneral=(boolean, default: dependent on various settings) Determines, if the button should be stored in generals without FULL.

+ attributes of a button, see [Button]


[Enclosure999]
Enclosure is a swell pedal. It consists of non-gui attributes describing its function. If it is displayed, it contains additional GUI attributes. Best practise is to specify enclosures in natural layout order (leftmost ﬁrst) and give them incremental values of MIDIInputNumber to make initial conﬁgurations easy for the user.

OPTIONAL ATTRIBUTES :
Name=(string) Name of the control
AmpMinimumLevel=(integer 0-100, required) Minimum volume, if the enclosure is closed.
MIDIInputNumber=(integer 0 - 200, default: 0) This number is used while building the initial MIDI conﬁguration to map the enclosure object to one MIDI device the user can specify for the respective enclosure. A value of 0 means no association, 1 means enclosure 1, 2 is enclosure 2 etc. Please note, that the GUI only allows the association of the ﬁrst few enclosures.
Displayed=(boolean, default: false for the new panel format, otherwise true) If true, the enclosure is visible on the main panel.

GUI attributes (are all OPTIONAL) :
DispLabelColour=(color, default: Dark Red) Color for the label text.
DispLabelFontSize=(font size, default: 7) Size of the label font.
DispLabelFontName=(string, default: empty) Font for the text. Empty means use the default font.
DispLabelText=(string, default: Name of the button) Content of the text label. You should edit it if you need to display a shorter string.

EnclosureStyle=(integer 1 - 4, default: implementation dependent) Select a built-in enclosure style (see image below).
§§OdfEdit_res/EnclosureStyle.png

BitmapCount=(integer 1 - 127, default: implementation dependent) Number of bitmaps/steps.
Bitmap999=(string, default: use internal bitmap) Specify the ﬁle name of an image to use as on bitmap for position 999. If the bitmap contains a mask for transparency, it will be used. All bitmaps must have the same size.
Mask999=(string, default: empty) File name for a external mask for bitmap 999. If empty, no mask is added.

PositionX=(integer 0 - panel width, default: according to layout model) Allow to override X position for enclosure.
PositionY=(integer 0 - panel height, default: according to layout model) Allow to override Y position for enclosure.
Width=(integer 0 - panel width, default: bitmap width) Width of the enclosure. If larger than the bitmap, the bitmap is tiled.
Height=(integer 0 - panel height, default: bitmap height) Height of the enclosure. If larger than the bitmap, the bitmap is tiled.
TileOffsetX=(integer 0 - bitmap width, default: 0) X position on the bitmap of the left pixel of the enclosure.
TileOffsetY=(integer 0 - bitmap height, default: 0) Y position on the bitmap of the top pixel of the enclosure.

MouseRectLeft=(integer 0 - Width, default: 0) relative X of left border of the mouse rectangle.
MouseRectTop=(integer 0 - Height, default: implementation dependent) relative Y of top border of the mouse rectangle.
MouseRectWidth=(integer 0 - Width, default: Width) width of the mouse rectangle.
MouseRectHeight=(integer 0 - Height, default: implementation dependent) height of the mouse rectangle.
MouseAxisStart=(integer 0 - MouseRectHeight, default: implementation dependent) top Y coordinate of the axis.
MouseAxisEnd=(integer MouseAxisStart - MouseRectHeight, default: implementation dependent) bottom Y coordinate of the axis.

TextRectLeft=(integer 0 - Width, default: 0) relative X of left border of the text rectangle.
TextRectTop=(integer 0 - Height, default: implementation dependent) relative Y of top border of the text rectangle.
TextRectWidth=(integer 0 - Width, default: Width) width of the text rectangle.
TextRectHeight=(integer 0 - Height, default: implementation dependent) height of the text rectangle.
TextBreakWidth=(integer 0 - text rectangle width, default: TextWidth) If 0, no text is displayed. Otherwise the value speciﬁes the maximum line length used for text breaking.


[General999]
General is a push button with the following additional combination data store attributes (used to store one combination).

REQUIRED ATTRIBUTES :
NumberOfCouplers=(integer 0 - number of coupler deﬁned in the ODF, required) Number of coupler states stored in this combination. The entries are called CouplerNumber999 and CouplerManual999.
NumberOfDivisionalCouplers=(integer 0 - divisional coupler count, required if storing of divisional coupler in the generals is enabled) Number of divisional coupler state stored in this combination. The entries are called DivisionalCouplerNumber999.
NumberOfStops=(integer 0 - number of stops deﬁned in the ODF, required) Number of stop states stored in this combination. The entries are called StopNumber999 and StopManual999.
NumberOfTremulants=(integer 0 - tremulant count, required) Number of tremulant states stored in this combination. The entries are called TremulantNumber999.

CouplerNumber999=(integer -999 - 999, required) Number of the coupler on the manual. If the value is negative, it is turned off, else it is turned on.
CouplerManual999=(integer manual number, required) Number of the manual, which contains the coupler.
DivisionalCouplerNumber999=(integer -divisional coupler count -divisional coupler count, required) Number of the divisional coupler. If the value is negative, it is turned off, else it is turned on.
StopNumber999=(integer -manual stop count - manual stop count, required) Number of the stop on the manual. If the value is negative, it is turned off, else turned on.
StopManual999=(integer manual number, required) Number of the manual, which contains the stop.
SwitchNumber999=(integer -switch count - switch count, required) Number of the switch. If the value is negative, it is turned off, else it is turned on.
TremulantNumber999=(integer -tremulant count - tremulant count, required) Number of the tremulant. If the value is negative, it is turned off, else turned on.

OPTIONAL ATTRIBUTES :
NumberOfSwitches=(integer 0 - switch count, default: 0) Number of switch states stored in this combination. The entries are called SwitchNumber999.
Protected=(boolean, default: false) If true, the stored combination cannot be changed.

+ attributes of a push button, see [PushButton]


[Image999]
Image allows to display an image on a panel. It tiles the image if it is bigger than the image object size.

REQUIRED ATTRIBUTES :
Image=(string, required) Speciﬁes the ﬁle name of an image to use as a bitmap. If the bitmap contains a mask for transparency, it will be used.

OPTIONAL ATTRIBUTES :
Mask=(string, default: empty) File name for a external mask for the bitmap. If empty, no mask is added.
PositionX=(integer 0 - panel width, default: 0) X coordinate of the left side. to override X position for button.
PositionY=(integer 0 - panel height, default: 0) Y coordinate of the left side.
Width=(integer 0 - panel width, default: bitmap width) Width of the button. If larger than the bitmap, the bitmap is tiled.
Height=(integer 0 - panel height, default: bitmap height) Height of the button. If larger than the bitmap, the bitmap is tiled.
TileOffsetX=(integer 0 - bitmap width, default: 0) X position on the bitmap of the left pixel of the button.
TileOffsetY=(integer 0 - bitmap width, default: 0) Y position on the bitmap of the top pixel of the button.


[Label999]
Label allows to display a text label on a panel. The background is an image. It is tiled if the image is smaller than the label area.

OPTIONAL ATTRIBUTES :
Name=(string, default: empty) The text to display on this object
FreeXPlacement=(boolean, default: true) True means that the X position is determined by DispXpos, else by DispDrawstopCol and DispSpanDrawstopColToRight.
FreeYPlacement=(boolean, default: true) True means that the Y position is determined by DispYpos, else by DispAtTopOfDrawstopCol.
DispXpos=(integer 0-panel width, default: 0) absolute X position.
DispYpos=(integer 0-panel height, default: 0) absolute Y position.
DispAtTopOfDrawstopCol=(boolean, required if FreeYPlacement is false) If true, the label is displayed above the drawstop, else below.
DispDrawstopCol=(integer 1- number of drawstop columns, required if FreeXPlacement is false) Position label at the speciﬁed drawstop column.
DispSpanDrawstopColToRight=(boolean, required if FreeXPlacement is false) If true, move label half of the drawstop to the right.
DispLabelColour=(color, default: black) Color for the label text.
DispLabelFontSize=(font size, default: normal) Size of the label font.
DispLabelFontName=(string, default: empty) Font for the text. Empty means use the group label font of the panel.
DispImageNum=(integer 1-12, default: 1) Builtin bitmap set to use (see image below).
§§OdfEdit_res/ImageNumLabel.png

Image=(string, default: use internal bitmap according to DispImageNum) Specify the ﬁle name of an image to use as bitmap. If the bitmap contains a mask for transparency, it will be used.
Mask=(string, default: empty) File name for a external mask for the bitmap. If empty, no mask is added.

PositionX=(integer 0 - panel width, default: according to the deﬁnitions above) Allow to override X position for button.
PositionY=(integer 0 - panel height, default: according to deﬁntions above) Allow to override Y position for button.
Width=(integer 0 - panel width, default: bitmap width) Width of the button. If larger than the bitmap, the bitmap is tiled.
Height=(integer 0 - panel height, default: bitmap height) Height of the button. If larger than the bitmap, the bitmap is tiled.
TileOffsetX=(integer 0 - bitmap width, default: 0) X position on the bitmap of the left pixel of the button.
TileOffsetY=(integer 0 - bitmap height, default: 0) Y position on the bitmap of the top pixel of the button.

TextRectLeft=(integer 0 - Width, default: 0) relative X of left border of the text rectangle.
TextRectTop=(integer 0 - Height, default: 0) relative Y of top border of the text rectangle.
TextRectWidth=(integer 0 - Width, default: Width) width of the text rectangle.
TextRectHeight=(integer 0 - Height, default: Height) height of the text rectangle.
TextBreakWidth=(integer 0 - text rectangle width, default: Width) If 0, no text is displayed. Otherwise the value speciﬁes the maximum line length used for text breaking.


[Manual999]
Manual is associated with a number of stops, tremulants, divisionals and couplers. The accessible range can be played via MIDI, the rest of the logical keys can only be triggered by (octave) couplers.
Best practise is to specify the visible manuals in the order of appearance, lowest ﬁrst. Invisible manuals and those used for special effects should be speciﬁed after the visible ones.

REQUIRED ATTRIBUTES :
Name=(string, required) Name of the manual.
NumberOfLogicalKeys=(integer 1-192, required) Number of keys on this manual (including non-playable ones).
FirstAccessibleKeyLogicalKeyNumber=(integer 1 - NumberOfLogicalKeys, required) number of the ﬁrst usable key.
FirstAccessibleKeyMIDINoteNumber=(integer 0 - 127, required) MIDI note number of the ﬁrst MIDI acessible key.

NumberOfAccessibleKeys=(integer 0 - 85, required) number of MIDI accessible keys.
NumberOfCouplers=(integer 0-999, default: 0) Number of couplers associated with this manual. Starting with 1, for each coupler, there is a Coupler999 setting.
NumberOfDivisionals=(integer 0-999, default: 0) Number of divisionals associated with this manual. Starting with 1, for each divisional, there is a Divisional999 setting.
NumberOfStops=(integer 0-999, required) Number of stops associated with this manual. Starting with 1, for each stop, there is a Stop999 setting.
NumberOfSwitches=(integer 0 - number of switches, default: 0) Number of switches associated with this manual. Starting with 1, for each switch, there is a Switch999 setting.
NumberOfTremulants=(integer 0 - number of tremulants, default: 0) Number of tremulants associated with this manual. Starting with 1, for each tremulant, there is a Tremulant999 setting.

Coupler999=(integer, required) Number of the Coupler999 section containing the coupler details.
Divisional999=(integer, required) Number of the Divisional999 section containg the coupler details.
Stop999=(integer, required) Number of the Stop999 section containing the stop details.
Switch999=(integer, required) Number of the Switch999 section containg the switch details.
Tremulant999=(integer, required) Number of the Tremulant999 section containg the tremulant details.

OPTIONAL ATTRIBUTES :
MIDIKey000 - MIDIKey127=(integer 0-127, default: same MIDI key number) Allows to map the MIDI note in MIDIKey999 to a different number. This mapping is used by the default manual MIDI matching type - others may or may not use this mapping table.
MIDIInputNumber=(integer 0 - 200, default: 0) This number is used while building the initial MIDI conﬁguration to map the manual object to what MIDI device the the user has set for the respective pedal/manual. 0 means no association. 1 maps to pedal, 2 to ﬁrst manual, 3 to second manual etc. NOTE: the GUI only allows the association of the ﬁrst few manuals. Second touch manuals can be set to the same number as the main manual as the user then only has to conﬁgure the low velocity to make it work.
Displayed=(boolean, default: false) If true, the manual is visible on the main panel.

The various GUI manual attributes are speciﬁed for the different key types. They are named: C, Cis, D, Dis, E, F, Fis, G, Gis, A, Ais, B.
If it is the ﬁrst key on the manual, it is preﬁxed with First. If it is the last key on the manual, it is preﬁxed with Last. So valid values are eg. Gis, FirstDis, LastAis.
In the following, these values will be marked as KEYTYPE.

If the manual is displayed, it contains the following OPTIONAL GUI attributes:
PositionX=(integer 0 - panel width, default: according to layout model) Allow to override X position for manual.
PositionY=(integer 0 - panel height, default: according to layout model) Allow to override Y position for manual.

ImageOn_KEYTYPE=(string, default: implementation dependent bitmap) Bitmap for the speciﬁed key type, if the key is pressed. The bitmap may contain a mask.
ImageOff_KEYTYPE=(string, default: implementation dependent bitmap) Bitmap for the speciﬁed key type, if the key is not pressed. The bitmap may contain a mask.
MaskOn_KEYTYPE=(string, default: empty string) Mask for the corresponding On bitmap. If empty, no external mask is loaded.
MaskOff_KEYTYPE=(string, default: corresponding on mask) Mask for the corresponding Off bitmap. If empty, no external mask is loaded.
Width_KEYTYPE=(integer 0 - 500, default: implementation dependent) This value is added to the x position of the current key to determine the position of the next key.
Offset_KEYTYPE=(integer -500 - 500, default: implementation dependent) This value can be used to adjust the display of the current key, eg. to place a sharp key overlapped with the previous key.
YOffset_KEYTYPE=(integer 0 - 500, default: 0) This value is can be used to adjust the Y coordinate of the current key.

Key999ImageOn=(string, default: corresponding ImageOn_KEYTYPE) Allows to set the on bitmap for the 999 key.
Key999ImageOff=(string, default: corresponding ImageOff_KEYTYPE) Allows to set the off bitmap for the 999 key.
Key999MaskOn=(string, default: corresponding MaskOn_KEYTYPE) Allows to set the on mask for the 999 key.
Key999MaskOff=(string, default: corresponding MaskOff_KEYTYPE) Allows to set the off mask for the 999 key.
Key999Width=(integer 0 - 500, default: corresponding Width_KEYTYPE) Allows to set the width of the 999 key.
Key999Offset=(integer -500 - 500, default: corresponding Offset_KEYTYPE) This value is can be used to adjust the display of the 999 key, eg. to place a sharp key overlapped with the previous 999 key.
Key999YOffset=(integer 0 - 500, default: corresponding YOffset_KEYTYPE) This value is can be used to adjust the Y coordinate of the 999 key.
Key999MouseRectLeft=(integer 0 - key bitmap width - 1 , default: 0) relative X of left border of the mouse rectangle.
Key999MouseRectTop=(integer 0 - key bitmap height - 1, default: 0) relative Y of top border of the mouse rectangle.
Key999MouseRectWidth=(integer 0 - key bitmap width, default: key bitmap width) width of the mouse rectangle.
Key999MouseRectHeight=(integer 0 - key bitmap height, default: key bitmap height) height of the mouse rectangle.

DispKeyColourInverted=(boolean, default: false) True means, the black keys are drawn in a light color while the white keys are drawn in a dark color.
DispKeyColourWooden=(boolean, default: false) True means, that a wood background is used for the keys.
DisplayFirstNote=(integer 0 - 127, default: FirstAccessibleKeyMIDINoteNumber) Display the ﬁrst key as the following note.

DisplayKeys=(integer 1 - NumberOfAccessibleKeys, default: NumberOfAccessibleKeys) number of keys to display.
DisplayKey999=(integer 0 - 127, default: FirstAccessibleKeyMIDINoteNumber + 999) The number in the key (999) is between 1 and DisplayKeys. It contains the midi number of the backend key, that is connected to this GUI key.
DisplayKey999Note=(integer 0 - 127, default: FirstAccessibleKeyMIDINoteNumber + 999) The number in the key (999) is between 1 and DisplayKeys. It contains the midi number of the displayed frontend GUI key.


[Panel999]
Panel000 is the main panel with new display format. Additional panels start with number 001. It includes the display metrics.
The layout of any panel is described by a layout model (see the below image). The available space is split vertically into three columns.
The left and the right columns contain drawstops laid out via a mesh.
The middle row is vertically divided:
- At the bottom, the pedal and its buttons are placed (if present).
- Above, an extra row of buttons may follow.
- The next row contains the enclosures.
- Then all manuals with their associated buttons follow.
- The two rows are a block of buttons and pistons.
The exact order can be speciﬁed via an attribute.

REQUIRED ATTRIBUTES (new panel format) :
Name=(string, required for non-main panels) Name of the panel.
HasPedals=(boolean, required) the panel includes a keyboard displayed as pedal.
NumberOfGUIElements=(integer 0-999, required for the main panel with new panel format, default 0 for any other panel) Number of elements on the panel. The section of the GUI elements are called Panel999Element999.

OPTIONAL ATTRIBUTES (new panel format) :
Group=(string, default: empty, only for non-main panels) If not empty, place it in the submenu with the speciﬁed name, else directly in the panel menu.
NumberOfImages=(integer 0-999, default: 0) Number of images on the panel. The section of the label GUI deﬁnitions are called Panel999Image999.

REQUIRED DISPLAY METRICS ATTRIBUTES (both new and old panel formats) :
DispScreenSizeHoriz=(panel size, required) Height of the panel.
DispScreenSizeVert=(panel size, required) Width of the panel.

DispDrawstopBackgroundImageNum=(bitmap number, required) Shown as 01 in the image below.
DispDrawstopInsetBackgroundImageNum=(bitmap number, required) Background of the drawstops columns pairs when DispPairDrawstopCols=Y
DispConsoleBackgroundImageNum=(bitmap number, required) Shown as 05 in the image below.
DispKeyHorizBackgroundImageNum=(bitmap number, required) Shown as 13 in the image below.
DispKeyVertBackgroundImageNum=(bitmap number, required) Shown as 20 in the image below.
§§OdfEdit_res/BackgroundRegion.png
Possible bitmap numbers are :
§§OdfEdit_res/BitmapNum.png

DispControlLabelFont=(string, required) Name of the font for button labels.
DispShortcutKeyLabelFont=(string, required) Name of the font for keyboard labels.
DispShortcutKeyLabelColour=(color, required) Color for shortcut labels
DispGroupLabelFont=(string, required) Font name for labels.

DispDrawstopCols=(integer 2-12, required) Number of drawstop columns. Must be even. NOTE: If you want more than 12 drawstop columns, you must use absolute positioning.
DispDrawstopRows=(integer 1-20, required) Number of drawstop rows. NOTE: If you want more than 20 drawstop rows you must use absolute positioning.
DispDrawstopColsOffset=(boolean, required) If true, each second row of drawstops on the left/right is displayed vertically shifted.
DispPairDrawstopCols=(boolean, required) Group two drawstop rows together. Number of drawstop rows must be divisible by 4.
DispExtraDrawstopRows=(integer 0-99, required) Number of drawstop rows in the center block. The row numbers start with 100.
DispExtraDrawstopCols=(integer 0 - 40, required) Number of drawstop columns in the center block.
DispButtonCols=(integer 1-32, required) Number of columns for displaying pistons in the center block.
DispExtraButtonRows=(integer 0-99, required) Number of rows for displaying extra pistons in the center block. The row numbers start with 100.
DispExtraPedalButtonRow=(boolean, required) Display an extra piston row with row number 9.
DispButtonsAboveManuals=(boolean, required) Display the pistons associated with the manual above (true) or below (false) the manual.
DispExtraDrawstopRowsAboveExtraButtonRows=(boolean, required) Display extra drawstop block above or below the extra piston block.

DispTrimAboveManuals=(boolean, required)
DispTrimBelowManuals=(boolean, required)
DispTrimAboveExtraRows=(boolean, required)

OPTIONAL DISPLAY METRICS ATTRIBUTES (both new and old panel formats) :
DispDrawstopWidth=(integer 1-150, default: 78) Drawstop width used for layout calculation.
DispDrawstopHeight=(integer 1-150, default: 69) Drawstop height used for layout calculation.
DispDrawstopOuterColOffsetUp=(boolean, required if DispDrawstopColsOffset is true) Determines if second row is shifted up or down.
DispPistonWidth=(integer 1-150, default: 44) Piston width used for layout calculation.
DispPistonHeight=(integer 1-150, default: 40) Piston height used for layout calculation.
DispEnclosureWidth=(integer 1-150, default: 52) Enclosure width used for layout calculation.
DispEnclosureHeight=(integer 1-150, default: 63) Enclosure width used for layout calculation.
DispPedalHeight=(integer 1-500, default: 40) Pedal height used for layout calculation.
DispPedalKeyWidth=(integer 1-500, default: 7) Width of one pedal key used for layout calculation.
DispExtraPedalButtonRowOffset=(boolean, required if DispExtraPedalButtonRow is true) Move extra pistons row slightly to the left.
DispExtraPedalButtonRowOffsetRight=(boolean, required if DispExtraPedalButtonRow is true) Move extra pistons row slightly to the right.
DispManualHeight=(integer 1-500, default: 32) Manual height used for layout calculation.
DispManualKeyWidth=(integer 1-500, default: 12) Width of one manual key used for layout calculation.

REQUIRED ATTRIBUTES (old panel format) :
Name=(string, required) Name of the panel.
HasPedals=(boolean, required) Includes a manual displayed as pedal.

NumberOfCouplers=(integer 0-999, required) Number of couplers on the panel. The section of the couplers GUI deﬁnitions are called Panel999Coupler999.
NumberOfDivisionals=(integer 0-999, required) Number of divisionals on the panel. The section of the divisionals GUI deﬁnitions are called Panel999Divisional999.
NumberOfDivisionalCouplers=(integer 0 - number of deﬁned divisional couplers, required) Number of divisional couplers on the panel. The section of the divisional coupler GUI deﬁnitions are called Panel999DivisionalCoupler999.
NumberOfEnclosures=(integer 0 - number of deﬁned enclosures, required) Number of enclosures on the panel. The section of the enclosures GUI deﬁnitions are called Panel999Enclosure999.
NumberOfGenerals=(integer 0 - number of deﬁned generals, required) Number of generals on the panel. The section of the generals GUI deﬁnitions are called Panel999General999.
NumberOfImages=(integer 0-999, required) Number of images on the panel. The section of the image GUI deﬁnitions are called Panel999Image999.
NumberOfLabels=(integer 0-999, required) Number of labels on the panel. The section of the label GUI deﬁnitions are called Panel999Label999.
NumberOfManuals=(integer 0 - number of deﬁned manuals) number of manuals to display on this panel.
NumberOfReversiblePistons=(integer 0 - number of deﬁned reversible pistons, required) Number of reversible pistons on the panel. The section of the reversible pistons GUI deﬁnitions are called Panel999ReversiblePiston999.
NumberOfStops=(integer 0-999, required) Number of stops on the panel. The section of the stops GUI deﬁnitions are called Panel999Stop999.
NumberOfTremulants=(integer 0 - number of deﬁned tremulants, required) Number of tremulant on the panel. The section of the tremulants GUI deﬁnitions are called Panel999Tremulant999.

Coupler999=(valid coupler number, required) Reference to the divisional on the main panel.
Coupler999Manual=(valid manual number, required) Reference to the manual of the coupler on the main panel.
Divisional999=(valid divisional number, required) Reference to the divisional on the main panel.
Divisional999Manual=(valid manual number, required) Reference to the manual of the divisional on the main panel.
DivisionalCoupler999=(valid divisional coupler number, required) Reference to the divisional coupler on the main panel.
Enclosure999=(valid enclosure number, required) Reference to the enclosure on the main panel.
General999=(valid general number, required) Reference to the general on the main panel.
Manual999=(valid manual number, required) Number of the manual to use a speciﬁed manual on the panel.
ReversiblePiston999=(valid reversible piston number, required) Reference to the reversible piston on the main panel.
Stop999=(valid stop number, required) Reference to the stop on the main panel.
Stop999Manual=(valid manual number, required) Reference to the manual of the stop on the main panel.
Switch999=(valid switch number, required) Reference to the switch on the main panel.
Tremulant999=(valid tremulant number, required) Reference to the tremulant on the main panel.

OPTIONAL ATTRIBUTES (old panel format) :
Group=(string, default: empty) If not empty, place it in the submenu with the speciﬁed name, else directly in the panel menu.
NumberOfSetterElements=(integer 0-999, default: 0) Number of setter elements on the panel. The section of the GUI deﬁnitions are called Panel999SetterElement999.
NumberOfSwitches=(integer 0 - number of deﬁned switches, default: 0) Number of switches on the panel. The section of the switches GUI deﬁnitions are called Panel999Switch999.


[Panel999Element999]
It displays one GUI element in the Panel999. The Type attribute describes the function (one type per object section), the other attributes depend on the function as described below.

REQUIRED ATTRIBUTES :
Type=Coupler
Manual=(valid manual number, required) Number of the manual.
Coupler=(valid coupler number, required) Number of the coupler on the manual.
+ attributes of a coupler, see [Coupler999]

Type=Divisional
Manual=(valid manual number, required) Number of the manual.
Divisional=(valid divisional number, required) Number of the divisional on the manual.
+ attributes of a divisional, see [Divisional999]

Type=DivisionalCoupler
DivisionalCoupler=(valid divisional coupler number, required) Number of the divisional coupler.
+ attributes of a divisional coupler, see [DivisionalCoupler999]

Type=Enclosure
Enclosure=(valid enclosure number, required) Number of the enclosure.
+ attributes of an enclosure, see [Enclosure999]

Type=General
General=(valid general number, required) Number of the general.
+ attributes of a general, see [General999]

Type=Label
+ attributes of a label, see [Label999]

Type=Manual
Manual=(valid manual number, required) Number of the manual.
+ attributes of a manual, see [Manual999]

Type=ReversiblePiston
ReversiblePiston=(valid reversible piston number, required) Number of the reversible piston.
+ attributes of a reversible piston, see [ReversiblePiston999]

Type=Stop
Manual=(valid manual number, required) Number of the manual.
Stop=(valid stop number, required) Number of the stop on the manual.
+ attributes of a stop, see [Stop999]

Type=Swell (Represents the crescendo swell)
+ attributes of an enclosure, see [Enclosure999]

Type=Switch
Switch=(valid switch number, required) Number of the switch.
+ attributes of a switch, see [Switch999]

Type=Tremulant
Tremulant=(valid tremulant number, required) Number of the tremulant.
+ attributes of a tremulant, see [Tremulant999]

Type=(a setter element, see the types in [SetterElement999])
+ attributes of a setter element, see [SetterElement999]


[Panel999Image999]
It displays one image in the Panel999. It tiles the image if it is bigger than image size.

attributes of an image, see [Image999]


[Panel999xxxxx999]
It displays one element xxxxx in the Panel999 (old panel format, xxxxx can be Coupler, Divisional, DivisionalCoupler, Enclosure, General, Label, ReversiblePiston, SetterElement, Stop, Switch or Tremulant).

attributes of a xxxxx, see [xxxxx999]


[Piston]
Piston is a push button which triggers other elements.

REQUIRED ATTRIBUTES :
ObjecType=(string, required) Type of the element to trigger. Value can be STOP, COUPLER, SWITCH or TREMULANT.
ManualNumber=(integer ﬁrst manual index - last manual index, required for stops and coupler) The manual, to which the referenced object belongs.
ObjectNumber=(integer, required) Determines the number of the object. Depending on the object it must be a valid stop/coupler/switch number on the referenced manual or a valid global tremulant number.

+ attributes of a push button, see [PushButton]


[PushButton]
Push button is a button without any state, used in Divisional, General or Piston objects. It is displayed as a piston.

attributes of a button, see [Button]


[Rank999]
Rank represents a row of pipes. It can either be part of a stop section or appear in its own section.
A rank section contains the attributes of each of its pipes too. The attributes of each pipe are preﬁxed with Pipe999 (number starting with 1) as described below.

REQUIRED ATTRIBUTES :
Name=(string, required) Name of the rank. The name may be presented to the user in lists too, therefore it should be descriptive.
FirstMidiNoteNumber=(integer 0-256, if the rank is part of a stop section, the default value is derived from the associated manuals. Otherwise required) Midi note number of the ﬁrst pipe.
WindchestGroup=(integer 1 - number of windchests, required) specify the windchest on which the pipes of the rank are placed.
Percussive=(boolean, required) If false, the samples are played as is (without any loop/release handling).

NumberOfLogicalPipes=(integer 1-192, required) Number of pipes in this rank.
Pipe999=(string, required) Relative path to the sample WAV ﬁle of the ﬁrst attack. It may be listed as REF:aa:bb:cc too. In that case, it means that this pipe is borrowed from manual aa, ﬁrst rank of stop bb, the pipe cc. It may contain DUMMY, which deﬁnes a non-sounding placeholder.

OPTIONAL ATTRIBUTES :
AmplitudeLevel=(ﬂoat 0-1000, default: 100) Linear amplitude scale factor applied to the whole rank. 100 means no change.
Gain=(ﬂoat -120 - 40, default: 0) Amplitude scale factor in dB applied to the whole rank. 0 means no change.
PitchTuning=(ﬂoat -1200-1200, default: 0) Retune the rank by the speciﬁed number of cents.
TrackerDelay=(integer 0 - 10000, default: 0) Delay introduced by the tracker for that rank.
HarmonicNumber=(ﬂoat 1-1024, default: 8) Harmonic number (= 64 / rank size), eg. 2 2/3 => 64 / (2 2/3) = 24. The harmonic number is used determining alternative tunings.
PitchCorrection=(ﬂoat -1200-1200, default: 0) Correction factor in cent for the pitch speciﬁed in the sample. This setting is used for retuning to other temperaments.
MinVelocityVolume=(ﬂoat 0-1000, default: 100) Linear amplitude scale factor at low velocity applied to the whole rank. 100 means no change.
MaxVelocityVolume=(ﬂoat 0-1000, default: 100) Linear amplitude scale factor at high velocity applied to the whole rank. 100 means no change.
AcceptsRetuning=(boolean, default: true) Determines if the rank will be retuned according to the current temperament. Retuning should be only disabled for sound effects.

Pipe999Percussive=(boolean, default: rank percussive setting) If false, the samples are played as is (without any loop/release handling).
Pipe999AmplitudeLevel=(ﬂoat 0-1000, default: 100) Linear amplitude scale factor applied to the pipe (in addition to the organ/rank factor). 100 means no change.
Pipe999Gain=(ﬂoat -120 - 40, default: 0) Amplitude scale factor in dB applied to the pipe (in addition to the organ/rank factor). 0 means no change.
Pipe999PitchTuning=(ﬂoat -1200-1200, default: 0) Retune this pipe the speciﬁed number of cents (in addition to the organ/rank factor).
Pipe999TrackerDelay=(integer 0 - 10000, default: 0) Delay introduced by the tracker for that pipe.
Pipe999LoadRelease=(boolean, default: reverse of percussive setting) If true, the release part is loaded from the ﬁrst attack sample.
Pipe999AttackVelocity=(int 0 - 127, default: 0) minimum velocity to use this attack sample.
Pipe999MaxTimeSinceLastRelease=(int -1 - 100000, default: -1) maximum time since the last release of the key to be able to use that attack. -1 means inﬁnite.
Pipe999IsTremulant=(int -1 - 1, default: -1) 1 means, that it is played, if the associated wave-based tremulant is on. 0 means, that it is played, if the associated wave-based tremulant is off. -1 means, that it is not affected by a wave-based tremulant.
Pipe999MaxKeyPressTime=(int -1 - 100000, default: -1) Up to this time value in ms, the release sample is chosen. -1 means inﬁnite.
Pipe999AttackStart=(int 0 - 158760000, default: 0) Allows to override the start of the sample. This option is speciﬁed in samples.
Pipe999CuePoint=(int -1 - 158760000, default: -1) Allows to override the cue point for the release. -1 means use from the wave ﬁle. This option is speciﬁed in samples.
Pipe999ReleaseEnd=(int -1 - 158760000, default: -1) Allows to override the end of the release. -1 means play till the end of the wav. This option is speciﬁed in samples.
Pipe999HarmonicNumber=(ﬂoat 1-1024, default: rank harmonic number) Harmonic number (= 64 / rank size), eg. 2 2/3 => 64 / (2 2/3) = 24.
Pipe999MIDIKeyNumber=(integer -1 - 127, default: -1) If -1, use pitch information from the Pipe999 sample, else override the information in the sample with this midi note number (Pipe999PitchCorrection is used for speciﬁng the fraction). Specifying the midi note number also reset the pitch fraction in the sample to 0.
Pipe999PitchCorrection=(ﬂoat -1200-1200, default: rank pitch correction) Correction factor in cent for the pitch speciﬁed in the sample. This setting is used for retuning to other temperaments.
Pipe999AcceptsRetuning=(boolean, default: rank setting) Determines if the pipe will be retuned according to the current temperament. Retuning should be only disabled for sound effects.
Pipe999WindchestGroup=(interger 1 - number of windchests, default: rank windchest) specify the windchest, on which this pipe is placed.
Pipe999MinVelocityVolume=(ﬂoat 0-1000, default: corresponding rank setting) Linear amplitude scale factor at low velocity applied to the pipe. 100 means no change.
Pipe999MaxVelocityVolume=(ﬂoat 0-1000, default: corresponding rank setting) Linear amplitude scale factor at high velocity applied to the pipe. 100 means no change.

Pipe999LoopCount=(int 0 - 100, default: 0) Allows to override the loops in the WAV ﬁle. 0 means use loops from the wave ﬁle.
Pipe999Loop999Start=(int 0 - 158760000, default: 0) Start sample of the loop. The value must be within the WAV ﬁle. This option is speciﬁed in samples.
Pipe999Loop999End=(int Pipe999Loop999Start + 1 - 158760000, required if Pipe999LoopCount is not zero) End sample of the loop. The value must be within the WAV ﬁle. This option is speciﬁed in samples.

Pipe999AttackCount=(int 0 - 100, default: 0) Number of additional attack samples.
Pipe999Attack999=(string, required) Relative path to the sample WAV ﬁle.
Pipe999Attack999LoadRelease=(boolean, default: reverse of percussive setting) If true, the release part is loaded.
Pipe999Attack999AttackVelocity=(int 0 - 127, default: 0) minimum velocity to use this attack sample.
Pipe999Attack999MaxTimeSinceLastRelease=(int -1 - 100000, default: -1) maximum time since the last release of the key to be able to use that attack. -1 means inﬁnite.
Pipe999Attack999IsTremulant=(int -1 - 1, default: -1) 1 means, that it is played, if the associated wave-based tremulant is on. 0 means, that it is played, if the associated wave-based tremulant is off. -1 means, that it not affected by a wave-based tremulant.
Pipe999Attack999MaxKeyPressTime=(int -1 - 100000, default: -1) Up to this time value in ms, the release sample is choosen. -1 means inﬁnite.
Pipe999Attack999AttackStart=(int 0 - 158760000, default: 0) Allows to override the start of the sample. This option is speciﬁed in samples.
Pipe999Attack999CuePoint=(int -1 - 158760000, default: -1) Allows to override the cue point for the release. -1 means use from the wave ﬁle. This option is speciﬁed in samples.
Pipe999Attack999ReleaseEnd=(int -1 - 158760000, default: -1) Allows to override the end of the release. -1 means play till the end of the wav. This option is speciﬁed in samples.
Pipe999Attack999LoopCount=(int 0 - 100, default: 0) Allows to override the loops in the WAV ﬁle. 0 means use loops from the wave ﬁle.
Pipe999Attack999Loop999Start=(int 0 - 158760000, default: 0) Start sample of the loop. The value must be within the WAV ﬁle. This option is speciﬁed in samples.
Pipe999Attack999Loop999End=(int Pipe999Attack999Loop999Start + 1 - 158760000, required if Pipe999LoopCount is not zero) End sample of the loop. The value must be within the WAV ﬁle. This option is speciﬁed in samples.

Pipe999ReleaseCount=(int 0 - 100, default: 0) Number of additional release samples.
Pipe999Release999=(string, required) Relative path to the sample WAV ﬁle.
Pipe999Release999IsTremulant=(int -1 - 1, default: -1) 1 means, that it is played, if the associated wave-based tremulant is on. 0 means, that it is played, if the associated wave-based tremulant is off. -1 means, that it not affected by a wave-based tremulant.
Pipe999Release999MaxKeyPressTime=(int -1 - 100000, default: -1) Up to this time value in ms, the release sample is choosen. -1 means inﬁnite.
Pipe999Release999CuePoint=(int -1 - 158760000, default: -1) Allows to override the cue point for the release. -1 means use from the wave ﬁle.
Pipe999Release999ReleaseEnd=(int -1 - 158760000, default: -1) Allows to override the end of the release. -1 means play till the end of the wav. This option is speciﬁed in samples.

Pipe999LoopCrossfadeLength=(int 0 - 120, default: 0) Crossfade length in ms between loop start and loop end. A cross fade requires enough samples before the start of the loop.
Pipe999ReleaseCrossfadeLength=(int 0 - 200, default: 0) Crossfade length in ms between loop and the release (or other attacks). 0 means automatic selection.


[ReversiblePiston999]
Not defined in the GrandOrgue help, unknown attributes, probably at least the one of a switch.


[SetterElement999]
It is possible to display various setter elements on the panels. The Type attribute (one type per object section) describes the function, the other attributes depend on the function.

REQUIRED ATTRIBUTES :
Type=CrescendoLabel (Represents a label with crescendo state, ie the current step that the crescendo pedal is at, from 1 to 32)
+ attributes of a label, see [Label999]

Type=CrescendoA, CrescendoB, CrescendoC or CrescendoD (Buttons to switch between the various crescendo modes, displayed as button per default)
+ attributes of a button, see [Button]

Type=CrescendoPrev, CrescendoNext or CrescendoCurrent (Buttons for controling the crescendo combinations, displayed as button per default)
+ attributes of a button, see [Button]

Type=Current (Recall current number button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=Full (Button to enable storing all elements in the setter, restrictions from the ODF are ignored, displayed as button per default)
+ attributes of a button, see [Button]

Type=GC (General cancel button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=General01 - General50 (Buttons for the setter generals, displayed as button per default)
+ attributes of a button, see [Button]

Type=GeneralLabel (Represents a label with the general bank number)
+ attributes of a label, see [Label999]

Type=GeneralPrev or GeneralNext (Buttons for switching banks of the setter generals, displayed as button per default)
+ attributes of a button, see [Button]

Type=Home (Move to 000 button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=Insert or Delete (Buttons to insert/delete a combination, displayed as button per default)
+ attributes of a button, see [Button]

Type=L0, L1, L2, L3, L4, L5, L6, L7, L8 or L9 (Recall combination with the speciﬁed digit as last digit button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=M100, M10, M1, P1, P10 or P100 (+/- 1/10/100 button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=PitchLabel (Label displaying the current pitch shift of the organ)
+ attributes of a label, see [Label999]

Type=PitchP1, PitchP10, PitchP100, PitchM1, PitchM10 or PitchM100 (Buttons for controlling the organ pitch +1, +10, +100, -1, -10, -100 cent, displayed as button per default)
+ attributes of a button, see [Button]

Type=Prev, Next or Set (Prev/next/set button of the setter, displayed as button per default)
+ attributes of a button, see [Button]

Type=Regular, Scope or Scoped (Button to switch between the various setter modes, displayed as button per default)
+ attributes of a button, see [Button]

Type=Save (Save button, displayed as button per default)
+ attributes of a button, see [Button]

Type=SequencerLabel (Represents the current number of the setter)
+ attributes of a label, see [Label999]

Type=TemperamentLabel (Label displaying the current temperament of the organ)
+ attributes of a label, see [Label999]

Type=TemperamentPrev or TemperamentNext (Buttons for switching temperaments, displayed as button per default)
+ attributes of a button, see [Button]

Type=TransposeDown or TransposeUp (Buttons for transposing, displayed as button per default)
+ attributes of a button, see [Button]

Type=TransposeLabel (Label displaying the current transpose setting)
+ attributes of a label, see [Label999]


[Stop999]
Stop object is a drawstop which consists of a number of ranks. If the number of ranks is set to zero, the stop contains one rank, which is deﬁned in the stop section - else it references a list of ranks.
Only the accessible pipes can be triggered from the manual.

REQUIRED ATTRIBUTES :
FirstAccessiblePipeLogicalKeyNumber=(integer 1-128, required) The key number on the manual of the ﬁrst accessible pipe.
FirstAccessiblePipeLogicalPipeNumber=(integer 1 - 192, required if NumberOfRanks=0) The number of the ﬁrst pipe accessible from the manual. If NumberOfRanks is not 0, this setting is not necessary.

NumberOfAccessiblePipes=(integer 1 - 192, required) Number of pipes, that are playable from the manual starting from the ﬁrst acessible pipe.

Rank999=(integer 0 - rank count speciﬁed in the organ section, required) Reference to a rank from the organ section.

OPTIONAL ATTRIBUTES :
NumberOfRanks=(integer 0 - 999, default: 0) Number of referenced ranks. If zero, one rank deﬁnition is included in the stop section. The lists of references is speciﬁed via the Rank999... settings.

Rank999FirstPipeNumber=(integer 1 - number of pipes in the rank, default: 1) Number of ﬁrst mapped pipe from the rank.
Rank999PipeCount=(integer 0 - remaining number of pipes in the rank, default: remaining number of pipes in the rank) Number of pipes mapped from the rank.
Rank999FirstAccessibleKeyNumber=(integer 1 - NumberOfAccessiblePipes, default: 1) Key number offset (starting with FirstAccessiblePipeLogicalKeyNumber) for the pipe referenced by Rank999FirstPipeNumber.

+ attributes of a rank if NumberOfRanks is zero, see [Rank999]
+ attributes of a drawstop, see [DrawStop]


[Switch999]
Switch is a drawstop without any additional attributes. It can be used, for example, to trigger stop action noises and key action noises.

attributes of a drawstop, see [DrawStop]


[Tremulant999]
Tremulant is a drawstop with additional attributes.

REQUIRED ATTRIBUTES :
In case of synthesised tremulants :
Period=(integer 32-44100, required) Period of the tremulant in ms
StartRate=(integer 1-100, required) Determines the startup time of the tremulant.
StopRate=(integer 1-100, required) Determines the stop time of the tremulant.
AmpModDepth=(integer 1-100, required) Determines, how much the volume will be changed.

OPTIONAL ATTRIBUTES :
TremulantType=(enumeration, default: Synth) Type of the tremulant. Valid values are: Synth (synthesised tremulant) and Wave (tremulant based on different wave samples).

+ attributes of a drawstop, see [DrawStop]


[WindchestGroup999]
Windchest represents a wind-chest on which pipes of ranks are placed.

REQUIRED ATTRIBUTES :
NumberOfEnclosures=(integer 0 - enclosure count, required) Number of enclosures, which inﬂuence this windchest. The list is speciﬁed by the Enclosure999 entries in the windchest section.
NumberOfTremulants=(integer 0 - tremulant count, required) Number of tremulants, which inﬂuence this windchest. The list is specifed by the Tremulant999 entries in the windchest section.

Enclosure999=(integer 1 - enclosure count, required) Number of an enclosure, which inﬂuences this windchest.
Tremulant999=(integer 1 - tremulant count, required) Number of a tremulant, which inﬂuences this windchest.

OPTIONAL ATTRIBUTES :
Name=(string, default: implementation dependent) Display name of this windchest.
"""

# first line of code executed at the launch of the script
# if we are in the main execution environment, call the main function of the application
if __name__ == '__main__': main()

