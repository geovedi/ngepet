void OnStart() {
  ushort s_sep = StringGetCharacter("\\", 0);
  ushort u_sep = StringGetCharacter("_", 0);

  string filenames[];
  if (FileSelectDialog("Select files to download", NULL,
                       "Template files (*.tpl)|*.tpl|All files (*.*)|*.*",
                       FSD_ALLOW_MULTISELECT, filenames,
                       "data.tpl") > 0) {

    int total = ArraySize(filenames);
    for (int i = 0; i < total; i++) {
      string result[];
      int k = StringSplit(filenames[i], s_sep, result);
      string fname = result[k-1];
      ArrayFree(result);
      StringSplit(fname, u_sep, result);
      string symbol = result[2];
      ChartApplyTemplate(ChartOpen(symbol, 15), "\\Files\\" + filenames[i]);
    }
  } else {
    Print("Files not selected");
  }
}
