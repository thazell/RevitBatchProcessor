#
# Revit Batch Processor
#
# Copyright (c) 2017  Dan Rumery, BVN
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import clr
import System
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import ModelPathUtils
from Autodesk.Revit.Exceptions import OperationCanceledException, CorruptModelException, InvalidOperationException, ArgumentException

import exception_util
import path_util
import revit_file_util
import revit_dialog_util
import revit_failure_handling
import batch_rvt_util
from batch_rvt_util import ScriptDataUtil

OUTPUT_FUNCTION_CONTAINER = [None]

SCRIPT_DATA_FILE_PATH_CONTAINER = [None]
SCRIPT_DATA_CONTAINER = [None]

SCRIPT_DOCUMENT_CONTAINER = [None]
SCRIPT_UIAPPLICATION_CONTAINER = [None]

def SetOutputFunction(output):
  OUTPUT_FUNCTION_CONTAINER[0] = output
  return

def SetScriptDataFilePath(scriptDataFilePath):
  SCRIPT_DATA_FILE_PATH_CONTAINER[0] = scriptDataFilePath
  return

def SetScriptDocument(doc):
  SCRIPT_DOCUMENT_CONTAINER[0] = doc
  return

def SetUIApplication(uiapp):
  SCRIPT_UIAPPLICATION_CONTAINER[0] = uiapp
  return

def Output(m="", msgId=""):
  message = (("[" + str(msgId) + "]"+ " ") if msgId != "" else "") + m
  OUTPUT_FUNCTION_CONTAINER[0](message)
  return

def GetScriptDataFilePath():
  scriptDataFilePath = SCRIPT_DATA_FILE_PATH_CONTAINER[0]
  return scriptDataFilePath

def LoadScriptDatas():
  scriptDataFilePath = GetScriptDataFilePath()
  if scriptDataFilePath is None:
    raise Exception("ERROR: could not retrieve script data file path from host.")
  scriptDatas = ScriptDataUtil.LoadManyFromFile(scriptDataFilePath)
  if scriptDatas is None:
    raise Exception("ERROR: could not load script data file.")
  return scriptDatas

def GetCurrentScriptData():
  return SCRIPT_DATA_CONTAINER[0]

def SetCurrentScriptData(scriptData):
  SCRIPT_DATA_CONTAINER[0] = scriptData
  return

def GetRevitFilePath():
  return SCRIPT_DATA_CONTAINER[0].RevitFilePath.GetValue()

def GetOpenInUI():
  return SCRIPT_DATA_CONTAINER[0].OpenInUI.GetValue()

def GetProjectFolderName():
  projectFolderName = None
  revitFilePath = GetRevitFilePath()
  if not str.IsNullOrWhiteSpace(revitFilePath):
    projectFolderName = path_util.GetProjectFolderNameFromRevitProjectFilePath(revitFilePath)
  return projectFolderName

def GetDataExportFolderPath():
  return SCRIPT_DATA_CONTAINER[0].DataExportFolderPath.GetValue()

def GetSessionId():
  return SCRIPT_DATA_CONTAINER[0].SessionId.GetValue()

def GetTaskScriptFilePath():
  return SCRIPT_DATA_CONTAINER[0].TaskScriptFilePath.GetValue()

def GetTaskData():
  return SCRIPT_DATA_CONTAINER[0].TaskData.GetValue()

def GetSessionDataFolderPath():
  return SCRIPT_DATA_CONTAINER[0].SessionDataFolderPath.GetValue()

def GetShowMessageBoxOnTaskError():
  return SCRIPT_DATA_CONTAINER[0].ShowMessageBoxOnTaskScriptError.GetValue()

def GetEnableDataExport():
  return SCRIPT_DATA_CONTAINER[0].EnableDataExport.GetValue()

def GetRevitProcessingOption():
  return SCRIPT_DATA_CONTAINER[0].RevitProcessingOption.GetValue()

def GetCentralFileOpenOption():
  return SCRIPT_DATA_CONTAINER[0].CentralFileOpenOption.GetValue()

def GetDeleteLocalAfter():
  return SCRIPT_DATA_CONTAINER[0].DeleteLocalAfter.GetValue()

def GetDiscardWorksetsOnDetach():
  return SCRIPT_DATA_CONTAINER[0].DiscardWorksetsOnDetach.GetValue()

def GetProgressNumber():
  return SCRIPT_DATA_CONTAINER[0].ProgressNumber.GetValue()

def GetProgressMax():
  return SCRIPT_DATA_CONTAINER[0].ProgressMax.GetValue()

def GetScriptDocument():
  doc = SCRIPT_DOCUMENT_CONTAINER[0]
  return doc

def GetUIApplication():
  uiapp = SCRIPT_UIAPPLICATION_CONTAINER[0]
  return uiapp

def WithExceptionLogging(action, output):
  result = None
  try:
    result = action()
  except Exception, e:
    exception_util.LogOutputErrorDetails(e, output)
    raise
  return result

def GetWorksharingCentralModelPath(doc):
  centralModelPath = None
  try:
    centralModelPath = doc.GetWorksharingCentralModelPath()
  except InvalidOperationException, e:
    centralModelPath = None
  return centralModelPath

def GetCentralModelFilePath(doc):
  modelPath = GetWorksharingCentralModelPath(doc)
  filePath = (
      ModelPathUtils.ConvertModelPathToUserVisiblePath(modelPath)
      if modelPath is not None else
      str.Empty
    )
  return filePath

def GetActiveDocument(uiapp):
  uidoc = uiapp.ActiveUIDocument
  doc = uidoc.Document if uidoc is not None else None
  return doc

def SafeCloseWithoutSave(doc, isOpenedInUI, closedMessage, output):
  app = doc.Application
  try:
    if not isOpenedInUI:
      revit_file_util.CloseWithoutSave(doc)
      output()
      output(closedMessage)
  except InvalidOperationException, e:
    output()
    output("WARNING: Couldn't close the document!")
    output()
    output(str(e.Message))
  except Exception, e:
    output()
    output("WARNING: Couldn't close the document!")
    exception_util.LogOutputErrorDetails(e, output, False)
  app.PurgeReleasedAPIObjects()
  return

def WithOpenedDetachedDocument(uiapp, openInUI, centralFilePath, discardWorksets, documentAction, output):
  app = uiapp.Application
  result = None
  output()
  output("Opening detached instance of central file: " + centralFilePath)
  # TODO: decide if worksets should be closed or open (currently the script closes them)
  if openInUI:
    if discardWorksets:
      uidoc = revit_file_util.OpenAndActivateDetachAndDiscardWorksets(uiapp, centralFilePath)
    else:
      uidoc = revit_file_util.OpenAndActivateDetachAndPreserveWorksets(uiapp, centralFilePath, True)
    doc = uidoc.Document
  else:
    if discardWorksets:
      doc = revit_file_util.OpenDetachAndDiscardWorksets(app, centralFilePath)
    else:
      doc = revit_file_util.OpenDetachAndPreserveWorksets(app, centralFilePath, True)
  try:
    result = documentAction(doc)
  finally:
    SafeCloseWithoutSave(doc, openInUI, "Closed detached instance of central file: " + centralFilePath, output)
  return result

def WithOpenedNewLocalDocument(uiapp, openInUI, centralFilePath, localFilePath, documentAction, output):
  try:
    app = uiapp.Application
    result = None
    output()
    output("Opening local instance of central file: " + centralFilePath)
    output()
    output("New local file: " + localFilePath)
    # TODO: decide if worksets should be closed or open (currently the script closes them)
    if openInUI:
      uidoc = revit_file_util.OpenAndActivateNewLocal(uiapp, centralFilePath, localFilePath, True)
      doc = uidoc.Document
    else:
      doc = revit_file_util.OpenNewLocal(app, centralFilePath, localFilePath, True)
    try:
      result = documentAction(doc)
    finally:
      SafeCloseWithoutSave(doc, openInUI, "Closed local file: " + localFilePath, output)
  except ArgumentException, e:
    if e.Message == "The model is a local file.\r\nParameter name: sourcePath":
      output()
      output("ERROR: The model is a local file. Cannot create another local file from it!")
    else:
      raise
  return result

def WithOpenedDocument(uiapp, openInUI, revitFilePath, documentAction, output):
  app = uiapp.Application
  result = None
  output()
  output("Opening file: " + revitFilePath)
  # TODO: decide if worksets should be closed or open (currently the script closes them)
  if openInUI:
    uidoc = revit_file_util.OpenAndActivateDocumentFile(uiapp, revitFilePath)
    doc = uidoc.Document
  else:
    doc = revit_file_util.OpenDocumentFile(app, revitFilePath)
  try:
    result = documentAction(doc)
  finally:
    SafeCloseWithoutSave(doc, openInUI, "Closed file: " + revitFilePath, output)
  return result

def RunDetachedDocumentAction(uiapp, openInUI, centralFilePath, discardWorksets, documentAction, output):
  def revitAction():
    result = WithOpenedDetachedDocument(uiapp, openInUI, centralFilePath, discardWorksets, documentAction, output)
    return result    
  result = WithErrorReportingAndHandling(uiapp, revitAction, output)
  return result

def RunNewLocalDocumentAction(uiapp, openInUI, centralFilePath, localFilePath, documentAction, output):
  def revitAction():
    result = WithOpenedNewLocalDocument(uiapp, openInUI, centralFilePath, localFilePath, documentAction, output)
    return result    
  result = WithErrorReportingAndHandling(uiapp, revitAction, output)
  return result

def RunDocumentAction(uiapp, openInUI, revitFilePath, documentAction, output):
  def revitAction():
    result = WithOpenedDocument(uiapp, openInUI, revitFilePath, documentAction, output)
    return result
  result = WithErrorReportingAndHandling(uiapp, revitAction, output)
  return result

def WithErrorReportingAndHandling(uiapp, revitAction, output):
  def action():
    result = WithDocumentOpeningErrorReporting(revitAction, output)
    return result
  result = WithAutomatedErrorHandling(uiapp, action, output)
  return result

def WithDocumentOpeningErrorReporting(documentOpeningAction, output):
  try:
    result = documentOpeningAction()
  except OperationCanceledException, e:
    output()
    output("ERROR: The operation was canceled: " + e.Message)
    raise
  except CorruptModelException, e:
    output()
    output("ERROR: Model is corrupt: " + e.Message)
    raise
  return result

def WithAutomatedErrorHandling(uiapp, revitAction, output):
  def action():
    def action():
      result = revit_dialog_util.WithDialogBoxShowingHandler(uiapp, revitAction, output)
      return result
    result = revit_failure_handling.WithFailuresProcessingHandler(uiapp.Application, action, output)
    return result
  result = WithExceptionLogging(action, output)
  return result

