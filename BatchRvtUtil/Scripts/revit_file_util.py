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

from System import Environment
from System.IO import Path
import path_util

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

class CentralLockedCallback(ICentralLockedCallback):
  def __init__(self, shouldWaitForLockAvailabilityCallback):
    self.ShouldWaitForLockAvailabilityCallback = shouldWaitForLockAvailabilityCallback
    return
  def ShouldWaitForLockAvailability(self):
    return self.ShouldWaitForLockAvailabilityCallback()

def CreateTransactWithCentralOptions(shouldWaitForLockAvailabilityCallback=None):
  transactWithCentralOptions = TransactWithCentralOptions()
  if shouldWaitForLockAvailabilityCallback is not None:
    centralLockedCallback = CentralLockedCallback(shouldWaitForLockAvailabilityCallback)
    transactWithCentralOptions.SetLockCallback(centralLockedCallback)
  return transactWithCentralOptions

def CreateSynchronizeWithCentralOptions(
    comment=str.Empty,
    compact=True,
    saveLocalBefore=True,
    saveLocalAfter=True,
    relinquishOptions=None
  ):
  syncOptions = SynchronizeWithCentralOptions()
  syncOptions.Comment = comment
  syncOptions.Compact = compact
  syncOptions.SaveLocalBefore = saveLocalBefore
  syncOptions.SaveLocalAfter = saveLocalAfter
  if relinquishOptions is None:
    relinquishOptions = RelinquishOptions(relinquishEverything=True)
  syncOptions.SetRelinquishOptions(relinquishOptions)
  return syncOptions

def SynchronizeWithCentral(doc, comment=str.Empty):
  transactOptions = CreateTransactWithCentralOptions()
  syncOptions = CreateSynchronizeWithCentralOptions(comment=comment)
  doc.SynchronizeWithCentral(transactOptions, syncOptions)
  return

def ReloadLastest(doc):
  doc.ReloadLatest(ReloadLatestOptions())
  return

def CopyModel(app, sourceModelPath, destinationFilePath, overwrite=True):
  sourceModelPath = (
      sourceModelPath
      if isinstance(sourceModelPath, ModelPath) else
      ModelPathUtils.ConvertUserVisiblePathToModelPath(sourceModelPath)
    )
  app.CopyModel(
      sourceModelPath,
      destinationFilePath,
      overwrite
    )
  return

def CreateNewProjectFile(app, revitFilePath):
  newDoc = app.NewProjectDocument(app.DefaultProjectTemplate)
  saveAsOptions = SaveAsOptions()
  saveAsOptions.OverwriteExistingFile = True
  newDoc.SaveAs(revitFilePath, saveAsOptions)
  return newDoc

def OpenAndActivateBatchRvtTemporaryDocument(uiApplication):
  application = uiApplication.Application
  BATCHRVT_TEMPORARY_REVIT_FILE_PATH = Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
      "BatchRvt",
      "TemporaryProject." + application.VersionNumber + ".rvt"
    )
  if not path_util.FileExists(BATCHRVT_TEMPORARY_REVIT_FILE_PATH):
    path_util.CreateDirectoryForFilePath(BATCHRVT_TEMPORARY_REVIT_FILE_PATH)
    newDoc = CreateNewProjectFile(application, BATCHRVT_TEMPORARY_REVIT_FILE_PATH)
    newDoc.Close(False)
  uiDoc = uiApplication.OpenAndActivateDocument(BATCHRVT_TEMPORARY_REVIT_FILE_PATH)
  return uiDoc

def OpenNewLocal(application, modelPath, localModelPath, closeAllWorksets=False):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  if isinstance(localModelPath, str):
    localModelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(localModelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DoNotDetach
  worksetConfig = (
      WorksetConfiguration(WorksetConfigurationOption.CloseAllWorksets)
      if closeAllWorksets else
      WorksetConfiguration()
    )
  openOptions.SetOpenWorksetsConfiguration(worksetConfig)
  WorksharingUtils.CreateNewLocal(modelPath, localModelPath)
  return application.OpenDocumentFile(localModelPath, openOptions)

def OpenAndActivateNewLocal(uiApplication, modelPath, localModelPath, closeAllWorksets=False):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  if isinstance(localModelPath, str):
    localModelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(localModelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DoNotDetach
  worksetConfig = (
      WorksetConfiguration(WorksetConfigurationOption.CloseAllWorksets)
      if closeAllWorksets else
      WorksetConfiguration()
    )
  openOptions.SetOpenWorksetsConfiguration(worksetConfig)
  WorksharingUtils.CreateNewLocal(modelPath, localModelPath)
  return uiApplication.OpenAndActivateDocument(localModelPath, openOptions, False)

def OpenDetachAndPreserveWorksets(application, modelPath, closeAllWorksets=False):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DetachAndPreserveWorksets
  worksetConfig = (
      WorksetConfiguration(WorksetConfigurationOption.CloseAllWorksets)
      if closeAllWorksets else
      WorksetConfiguration()
    )
  openOptions.SetOpenWorksetsConfiguration(worksetConfig)
  return application.OpenDocumentFile(modelPath, openOptions)

def OpenAndActivateDetachAndPreserveWorksets(uiApplication, modelPath, closeAllWorksets=False):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DetachAndPreserveWorksets
  worksetConfig = (
      WorksetConfiguration(WorksetConfigurationOption.CloseAllWorksets)
      if closeAllWorksets else
      WorksetConfiguration()
    )
  openOptions.SetOpenWorksetsConfiguration(worksetConfig)
  return uiApplication.OpenAndActivateDocument(modelPath, openOptions, False)

def OpenDetachAndDiscardWorksets(application, modelPath):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DetachAndDiscardWorksets
  return application.OpenDocumentFile(modelPath, openOptions)

def OpenAndActivateDetachAndDiscardWorksets(uiApplication, modelPath):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  openOptions = OpenOptions()
  openOptions.DetachFromCentralOption = DetachFromCentralOption.DetachAndDiscardWorksets
  return uiApplication.OpenAndActivateDocument(modelPath, openOptions, False)

def OpenDocumentFile(application, modelPath):
  if isinstance(modelPath, ModelPath):
    modelPath = ModelPathUtils.ConvertModelPathToUserVisiblePath(modelPath)
  return application.OpenDocumentFile(modelPath)

def OpenAndActivateDocumentFile(uiApplication, modelPath):
  if isinstance(modelPath, ModelPath):
    modelPath = ModelPathUtils.ConvertModelPathToUserVisiblePath(modelPath)
  return uiApplication.OpenAndActivateDocument(modelPath)

def RelinquishAll(doc, shouldWaitForLockAvailabilityCallback=None):
  relinquishOptions = RelinquishOptions(True)
  transactWithCentralOptions = CreateTransactWithCentralOptions(shouldWaitForLockAvailabilityCallback)
  relinquishedItems = WorksharingUtils.RelinquishOwnership(doc, relinquishOptions, transactWithCentralOptions)
  return relinquishedItems

def SaveAsNewCentral(doc, modelPath, overwrite=True, clearTransmitted=False):
  saveAsOptions = SaveAsOptions()
  saveAsOptions.Compact = True
  saveAsOptions.OverwriteExistingFile = overwrite
  saveAsOptions.MaximumBackups = 1 # Can't set this to 0, unfortunately.
  worksharingSaveAsOptions = WorksharingSaveAsOptions()
  worksharingSaveAsOptions.SaveAsCentral = True
  worksharingSaveAsOptions.ClearTransmitted = clearTransmitted
  saveAsOptions.SetWorksharingOptions(worksharingSaveAsOptions)
  doc.SaveAs(modelPath, saveAsOptions)
  return

def CloseWithSave(doc):
  doc.Close(True)
  return

def CloseWithoutSave(doc):
  doc.Close(False)
  return

def Save(doc, compact=False, previewViewId=None):
  saveOptions = SaveOptions()
  saveOptions.Compact = compact
  if previewViewId is not None:
    saveOptions.PreviewViewId = previewViewId
  doc.Save(saveOptions)
  return

def SaveAs(
      doc,
      modelPath,
      overwriteExisting=False,
      compact=False,
      previewViewId=None,
      worksharingSaveAsOptions=None,
      maximumBackups=None
    ):
  if isinstance(modelPath, str):
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(modelPath)
  saveAsOptions = SaveAsOptions()
  saveAsOptions.Compact = compact
  saveAsOptions.OverwriteExistingFile = overwriteExisting
  if previewViewId is not None:
    saveAsOptions.PreviewViewId = previewViewId
  if worksharingSaveAsOptions is not None:
    saveAsOptions.SetWorksharingOptions(worksharingSaveAsOptions)
  if maximumBackups is not None:
    saveAsOptions.MaximumBackups = maximumBackups
  doc.SaveAs(modelPath, saveAsOptions)
  return

def CreateWorksharingSaveAsOptions(saveAsCentral=False, openWorksetsDefault=SimpleWorksetConfiguration.AskUserToSpecify, clearTransmitted=False):
  worksharingSaveAsOptions = WorksharingSaveAsOptions()
  worksharingSaveAsOptions.OpenWorksetsDefault = openWorksetsDefault
  worksharingSaveAsOptions.ClearTransmitted = clearTransmitted
  worksharingSaveAsOptions.SaveAsCentral = saveAsCentral
  return worksharingSaveAsOptions

def DetachAndSaveModel(app, centralModelFilePath, detachedModelFilePath):
  centralModelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(centralModelFilePath)
  CopyModel(app, centralModelPath, detachedModelFilePath)
  detachedModelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(detachedModelFilePath)
  doc = OpenDetachAndPreserveWorksets(app, detachedModelPath)
  SaveAsNewCentral(doc, detachedModelPath)
  # Relinquish ownership (Saving the new central file takes ownership of worksets so relinquishing must be done
  # after it, if at all)
  RelinquishAll(doc)
  return doc

def TryGetBasicFileInfo(revitFilePath):
  basicFileInfo = None
  try:
    basicFileInfo = BasicFileInfo.Extract(revitFilePath)
  except Exception, e:
    basicfileInfo = None
  return basicFileInfo

def GetRevitFileVersion(revitFilePath):
  basicFileInfo = TryGetBasicFileInfo(revitFilePath)
  savedInVersion = basicFileInfo.SavedInVersion if basicFileInfo is not None else None
  return savedInVersion

def IsLocalModel(revitFilePath):
  isLocalModel = False
  basicFileInfo = TryGetBasicFileInfo(revitFilePath)
  if basicFileInfo is not None:
    isWorkshared = basicFileInfo.IsWorkshared
    if isWorkshared:
      # NOTE: see: https://forums.autodesk.com/t5/revit-api-forum/basicfileinfo-iscreatedlocal-property-outputting-unexpected/td-p/7111503
      isLocalModel = (basicFileInfo.IsCreatedLocal or basicFileInfo.IsLocal)
  return isLocalModel

def IsCentralModel(revitFilePath):
  isCentralModel = False
  basicFileInfo = TryGetBasicFileInfo(revitFilePath)
  if basicFileInfo is not None:
    isWorkshared = basicFileInfo.IsWorkshared
    if isWorkshared:
      isCentralModel = basicFileInfo.IsCentral
  return isCentralModel

def IsWorkshared(revitFilePath):
  isWorkshared = False
  basicFileInfo = TryGetBasicFileInfo(revitFilePath)
  if basicFileInfo is not None:
    isWorkshared = basicFileInfo.IsWorkshared
  return isWorkshared

