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

clr.AddReference("System.Core")
import System.Linq
clr.ImportExtensions(System.Linq)
from System.Linq import Enumerable

import System.Reflection as Refl

import System.IO
from System.IO import IOException

from System.Reflection import TargetInvocationException

import System.Text
from System.Text import Encoding

clr.AddReference("WindowsBase")
import System.IO.Packaging as Packaging

import util

STORAGE_ROOT_TYPE_NAME = "System.IO.Packaging.StorageRoot"
STORAGE_ROOT_OPEN_METHOD_NAME = "Open"
BASIC_FILE_INFO_STREAM_NAME = "BasicFileInfo"

def GetWindowsBaseAssembly():
  return clr.GetClrType(Packaging.StorageInfo).Assembly

def GetStorageRootType():
  return GetWindowsBaseAssembly().GetType(STORAGE_ROOT_TYPE_NAME, True, False)

def InvokeStorageRootMember(storageRoot, methodName, *methodArgs):
  return GetStorageRootType().InvokeMember(
      methodName,
      Refl.BindingFlags.Static | Refl.BindingFlags.Instance |
      Refl.BindingFlags.Public | Refl.BindingFlags.NonPublic |
      Refl.BindingFlags.InvokeMethod,
      None,
      storageRoot,
      methodArgs.ToArray[object](),
    )

def GetStorageRoot(filePath):
  storageRoot = InvokeStorageRootMember(
        None,
        STORAGE_ROOT_OPEN_METHOD_NAME,
        filePath,
        System.IO.FileMode.Open,
        System.IO.FileAccess.Read,
        System.IO.FileShare.Read
      ) if not str.IsNullOrWhiteSpace(filePath) else None
  return storageRoot

def GetBasicFileInfoStream(storageRoot):
  return storageRoot.GetStreamInfo(BASIC_FILE_INFO_STREAM_NAME).GetStream()

def CreateByteBuffer(length):
  return Enumerable.Repeat[System.Byte](0, length).ToArray()

def ReadAllBytes(stream):
  length = int(stream.Length)
  buffer = CreateByteBuffer(length)
  readCount = stream.Read(buffer, 0, length)
  return buffer.Take(readCount).ToArray()

def GetRevitVersionText_OldMethod(revitFilePath):
  storageRoot = GetStorageRoot(revitFilePath)
  stream = GetBasicFileInfoStream(storageRoot)
  bytes = ReadAllBytes(stream)
  unicodeString = Encoding.Unicode.GetString(bytes)
  start = unicodeString.IndexOf("Autodesk Revit")
  end = unicodeString.IndexOf("\x00", start)
  versionText = unicodeString.Substring(start, end - start)
  return versionText.Substring(0, versionText.LastIndexOf(")") + 1) 

def GetBasicFileInfoBytes(revitFilePath):
  storageRoot = GetStorageRoot(revitFilePath)
  stream = GetBasicFileInfoStream(storageRoot)
  bytes = ReadAllBytes(stream)
  return bytes

def GetRevitFileVersionInfoText(revitFilePath):
  revitVersionInfoText = str.Empty
  bytes = GetBasicFileInfoBytes(revitFilePath)
  asciiString = Encoding.ASCII.GetString(bytes)
  TEXT_MARKER = '\r\n' # Most common delimiter around the text section.
  TEXT_MARKER_ALT = '\x04\r\x00\n\x00' # Alternative delimiter (occasionally encountered... not sure why though).
  textMarker = TEXT_MARKER
  textMarkerIndices = util.FindAllIndicesOf(asciiString, textMarker)
  numberOfTextMarkerIndices = len(textMarkerIndices)
  if numberOfTextMarkerIndices != 2:
    textMarker = TEXT_MARKER_ALT
    textMarkerIndices = util.FindAllIndicesOf(asciiString, textMarker)
    numberOfTextMarkerIndices = len(textMarkerIndices)
  if numberOfTextMarkerIndices == 2:
    startTextIndex = textMarkerIndices[0] + len(textMarker)
    endTextIndex = textMarkerIndices[1]
    textBytes = bytes[startTextIndex:endTextIndex]
    revitVersionInfoText = Encoding.Unicode.GetString(bytes[startTextIndex:endTextIndex])
  return revitVersionInfoText

def TryGetRevitFileVersionInfoText(revitFilePath):
  revitVersionInfoText = str.Empty
  try:
    revitVersionInfoText = GetRevitFileVersionInfoText(revitFilePath)
  except TargetInvocationException, e:
    revitVersionInfoText = str.Empty
  except IOException, e:
    revitVersionInfoText = str.Empty
  return revitVersionInfoText

def ExtractRevitVersionInfoFromText(revitVersionInfoText):
  REVIT_BUILD_PROPERTY = "Revit Build:"
  FORMAT_PROPERTY = "Format:"
  BUILD_PROPERTY = "Build:"
  revitVersionDescription = str.Empty
  lines = util.ReadLinesFromText(revitVersionInfoText)
  indexedLines = [[index, line] for index, line in enumerate(lines)]
  # Revit 2019 (and onwards?) has 'Build' and 'Format' properties instead of 'Revit Build'
  formatLine = indexedLines.SingleOrDefault(lambda l: l[1].StartsWith(FORMAT_PROPERTY))
  buildLine = indexedLines.SingleOrDefault(lambda l: l[1].StartsWith(BUILD_PROPERTY))
  if buildLine is not None:
    buildLineText = buildLine[1]
    buildLineText = buildLineText[len(BUILD_PROPERTY):]
    formatLineText = str.Empty
    if formatLine is not None:
      formatLineText = formatLine[1]
      formatLineText = formatLineText[len(FORMAT_PROPERTY):]
      revitVersionDescription = "Autodesk Revit " + formatLineText.Trim() + " (Build: " + buildLineText.Trim() + ")"
  else:
    revitBuildLine = indexedLines.SingleOrDefault(lambda l: l[1].StartsWith(REVIT_BUILD_PROPERTY))
    revitBuildLineText = str.Empty
    if revitBuildLine is None:
      # In rare cases the Revit Build *value* is on the next line for some reason!
      # In this scenario it seems to always be followed immediately (no spaces) by the 'Last Save Path:' property specifier
      revitBuildLine = indexedLines.SingleOrDefault(lambda l: l[1].Contains(REVIT_BUILD_PROPERTY))
      if revitBuildLine is not None:
        lineNumber = revitBuildLine[0]
        revitBuildLine = indexedLines[lineNumber+1]
        revitBuildLineText = revitBuildLine[1]
        indexOfLastSavePath = revitBuildLineText.IndexOf("Last Save Path:")
        revitBuildLineText = revitBuildLineText[:indexOfLastSavePath] if indexOfLastSavePath != -1 else revitBuildLineText
    else:
      revitBuildLineText = revitBuildLine[1]
      revitBuildLineText = revitBuildLineText[len(REVIT_BUILD_PROPERTY):]
    revitVersionDescription = revitBuildLineText.Trim()
  return revitVersionDescription

def GetRevitVersionText(revitFilePath):
  revitVersionInfoText = TryGetRevitFileVersionInfoText(revitFilePath)
  revitVersionText = ExtractRevitVersionInfoFromText(revitVersionInfoText)
  return revitVersionText


