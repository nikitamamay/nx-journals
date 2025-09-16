
def show_NX_message(title: str, msg: str):
    import NXOpen
    import NXOpen.UIStyler

    ui:NXOpen.UI = NXOpen.UI.GetUI()
    msgbox = ui.NXMessageBox
    msgbox.Show(title, NXOpen.NXMessageBoxDialogType.Information, msg)  # type: ignore

