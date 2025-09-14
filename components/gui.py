
import typing

import os
import logging

import math


import NXOpen
import NXOpen.BlockStyler
import NXOpen.Assemblies
import NXOpen.UIStyler


import this_logging
logger = this_logging.getLogger(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(BASE_DIR, "icons")
DLX_FILE = os.path.join(BASE_DIR, "dialog.dlx")




"""
Tkinter не работает!!!
"""
# import tkinter

# tk = tkinter.Tk()
# frame = tkinter.Frame(tk, relief=tkinter.RIDGE, borderwidth=2)
# frame.pack(fill=tkinter.BOTH,expand=1)
# label = tkinter.Label(frame, text="Hello, World")
# label.pack(fill=tkinter.X, expand=1)
# button = tkinter.Button(frame,text="Exit",command=tk.destroy)
# button.pack(side=tkinter.BOTTOM)
# tk.mainloop()






def show_error(msg: str, title: str = "Error") -> None:
    try:
        ui:NXOpen.UI = NXOpen.UI.GetUI()
        msgbox = ui.NXMessageBox
        msgbox.Show(title, NXOpen.NXMessageBoxDialogType.Error, msg)  # type: ignore
    except:
        logger.warning("Cannot show NX GUI message box with error message")

def ask_question(msg: str, title: str = "Question") -> bool:
    try:
        ui:NXOpen.UI = NXOpen.UI.GetUI()
        msgbox = ui.NXMessageBox
        rc = msgbox.Show(title, NXOpen.NXMessageBoxDialogType.Question, msg)  # type: ignore
        return rc == 1
    except:
        logger.warning("Cannot show NX GUI message box with error message")
    return False






class dialog:
    """
    Еще с диалогом есть такая проблема, что он сам создает одну единственную
    undoMark и игнорирует создание моих undoMarks. Но зато можно потом сделать
    redo для действий диалога.
    """
    # static class members
    theSession = None
    theUI = None

    def __init__(self):
        self.theSession = NXOpen.Session.GetSession()
        self.theUI = NXOpen.UI.GetUI()
        self.theDlxFileName = DLX_FILE
        self.theDialog: NXOpen.BlockStyler.BlockDialog = self.theUI.CreateDialog(self.theDlxFileName)
        self.theDialog.AddUpdateHandler(self.update_cb)
        self.theDialog.AddInitializeHandler(self.initialize_cb)
        self.theDialog.AddDialogShownHandler(self.dialogShown_cb)

        self.callbacks = {}

    def Show(self):
        self.theDialog.Show()


    def Dispose(self):
        if self.theDialog != None:
            self.theDialog.Dispose()
            self.theDialog = None

    def initialize_cb(self):
        self.selection0: NXOpen.BlockStyler.SelectObject = self.theDialog.TopBlock.FindBlock("selection0")
        self.selection0.AddFilter(NXOpen.BlockStyler.SelectObject.FilterType.Components)

        self.group = self.theDialog.TopBlock.FindBlock("group")
        # self.listbox_pending = self.theDialog.TopBlock.FindBlock("listbox_pending")
        self.btn_pending_0: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_pending_0")
        self.btn_pending_0.Bitmap = os.path.join(ICONS_DIR, "add_pending.bmp")
        self.btn_pending_recursive: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_pending_recursive")
        self.btn_pending_recursive.Bitmap = os.path.join(ICONS_DIR, "add_pending_recursive.bmp")

        self.group0 = self.theDialog.TopBlock.FindBlock("group0")
        self.btn_000: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_000")
        self.btn_000.Bitmap = os.path.join(ICONS_DIR, "set_in_000.bmp")
        self.t_intensity = self.theDialog.TopBlock.FindBlock("t_intensity")
        self.t_X_neg: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_X_neg")
        self.t_X_pos: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_X_pos")
        self.t_Y_neg: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_Y_neg")
        self.t_Y_pos: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_Y_pos")
        self.t_Z_neg: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_Z_neg")
        self.t_Z_pos: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("t_Z_pos")

        self.group1 = self.theDialog.TopBlock.FindBlock("group1")
        self.listbox_refset = self.theDialog.TopBlock.FindBlock("listbox_refset")
        self.btn_refset_apply: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_refset_apply")
        self.btn_refset_apply.Bitmap = os.path.join(ICONS_DIR, "ref_sets.bmp")

        self.group2 = self.theDialog.TopBlock.FindBlock("group2")
        self.btn_fix: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_fix")
        self.btn_fix.Bitmap = os.path.join(ICONS_DIR, "fix.bmp")
        self.btn_fix_recursive: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_fix_recursive")
        self.btn_fix_recursive.Bitmap = os.path.join(ICONS_DIR, "fix_recursive.bmp")

        self.group3 = self.theDialog.TopBlock.FindBlock("group3")
        self.btn_freeze: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_freeze")
        self.btn_freeze.Bitmap = os.path.join(ICONS_DIR, "wave_freeze.bmp")
        self.btn_freeze_recursive: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_freeze_recursive")
        self.btn_freeze_recursive.Bitmap = os.path.join(ICONS_DIR, "wave_freeze_recursive.bmp")
        self.btn_unfreeze: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_unfreeze")
        self.btn_unfreeze.Bitmap = os.path.join(ICONS_DIR, "wave_unfreeze.bmp")
        self.btn_unfreeze_recursive: NXOpen.BlockStyler.Button = self.theDialog.TopBlock.FindBlock("btn_unfreeze_recursive")
        self.btn_unfreeze_recursive.Bitmap = os.path.join(ICONS_DIR, "wave_unfreeze_recursive.bmp")

        #------------------------------------------------------------------------------
        # Registration of ListBox specific callbacks
        #------------------------------------------------------------------------------
        # self.listbox_pending.SetAddHandler(self.AddCallback)

        # self.listbox_pending.SetDeleteHandler(self.DeleteCallback)

        # self.listbox_refset.SetAddHandler(self.AddCallback)

        # self.listbox_refset.SetDeleteHandler(self.DeleteCallback)

        #------------------------------------------------------------------------------


    def dialogShown_cb(self):
        # ---- Enter your callback code here -----
        pass

    def get_selected(self) -> 'list[NXOpen.Assemblies.Component]':
        """
        Проблема в том, что элемент выделения `SelectObject` в интерфейсе диалога NX
        не дает выбрать головную сборку в навигаторе сборки
        даже при снятии всех фильтров с него.
        """
        selected = self.selection0.GetSelectedObjects()
        logger.info(f"Selected objects are (len={len(selected)}): {selected}")
        return selected


    def update_cb(self, block: NXOpen.BlockStyler.UIBlock):
        try:
            logger.debug(f"update_cb() for block '{block.Name}'")
            if block == self.selection0:
                if "selection0" in self.callbacks:
                    self.callbacks["selection0"]()
            # if block == self.listbox_pending:
            #     if "listbox_pending" in self.callbacks:
            #         self.callbacks["listbox_pending"]()
            if block == self.btn_pending_0:
                if "btn_pending_0" in self.callbacks:
                    self.callbacks["btn_pending_0"]()
            if block == self.btn_pending_recursive:
                if "btn_pending_recursive" in self.callbacks:
                    self.callbacks["btn_pending_recursive"]()
            if block == self.btn_000:
                if "btn_000" in self.callbacks:
                    self.callbacks["btn_000"]()
            if block == self.t_intensity:
                if "t_intensity" in self.callbacks:
                    self.callbacks["t_intensity"]()
            if block == self.t_X_neg:
                if "t_X_neg" in self.callbacks:
                    self.callbacks["t_X_neg"]()
            if block == self.t_X_pos:
                if "t_X_pos" in self.callbacks:
                    self.callbacks["t_X_pos"]()
            if block == self.t_Y_neg:
                if "t_Y_neg" in self.callbacks:
                    self.callbacks["t_Y_neg"]()
            if block == self.t_Y_pos:
                if "t_Y_pos" in self.callbacks:
                    self.callbacks["t_Y_pos"]()
            if block == self.t_Z_neg:
                if "t_Z_neg" in self.callbacks:
                    self.callbacks["t_Z_neg"]()
            if block == self.t_Z_pos:
                if "t_Z_pos" in self.callbacks:
                    self.callbacks["t_Z_pos"]()
            if block == self.listbox_refset:
                if "listbox_refset" in self.callbacks:
                    self.callbacks["listbox_refset"]()
            if block == self.btn_refset_apply:
                if "btn_refset_apply" in self.callbacks:
                    self.callbacks["btn_refset_apply"]()
            if block == self.btn_fix:
                if "btn_fix" in self.callbacks:
                    self.callbacks["btn_fix"]()
            if block == self.btn_fix_recursive:
                if "btn_fix_recursive" in self.callbacks:
                    self.callbacks["btn_fix_recursive"]()
            if block == self.btn_freeze:
                if "btn_freeze" in self.callbacks:
                    self.callbacks["btn_freeze"]()
            if block == self.btn_freeze_recursive:
                if "btn_freeze_recursive" in self.callbacks:
                    self.callbacks["btn_freeze_recursive"]()
            if block == self.btn_unfreeze:
                if "btn_unfreeze" in self.callbacks:
                    self.callbacks["btn_unfreeze"]()
            if block == self.btn_unfreeze_recursive:
                if "btn_unfreeze_recursive" in self.callbacks:
                    self.callbacks["btn_unfreeze_recursive"]()
        except Exception as e:
            msg = f"Error with block '{block.Name}' update callback: {str(e)}"
            logger.error(msg, exc_info=True)
            show_error(msg)

    #------------------------------------------------------------------------------
    # ListBox specific callbacks
    #------------------------------------------------------------------------------
    # def AddCallback (self list_box):
    #
    #

    # def DeleteCallback(self, list_box):
    #
    #

    #------------------------------------------------------------------------------

    #------------------------------------------------------------------------------
    # Function Name: GetBlockProperties
    # Returns the propertylist of the specified BlockID
    #------------------------------------------------------------------------------
    def GetBlockProperties(self, blockID):
        return self.theDialog.GetBlockProperties(blockID)




def main():
    thedialog = None
    try:
        thedialog =  dialog()
        #  The following method shows the dialog immediately
        thedialog.Show()
    except Exception as ex:
        # ---- Enter your exception handling code here -----
        NXOpen.UI.GetUI().NXMessageBox.Show("Block Styler", NXOpen.NXMessageBox.DialogType.Error, str(ex))
    finally:
        if thedialog != None:
            thedialog.Dispose()
            thedialog = None



if __name__ == '__main__':
    main()

