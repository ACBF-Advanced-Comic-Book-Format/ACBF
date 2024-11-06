; Copyright 2018 Robert Kubik
;
; -------------------------------------------------------------------------
; This program is free software; you can redistribute it and/or modify
; it under the terms of the GNU General Public License version 3 as published
; by the Free Software Foundation.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program; if not, write to the Free Software
; -------------------------------------------------------------------------


Unicode true

!define ACBFV_NAME "ACBF Viewer"
!define ACBFV_ID "acbfv"
!define ACBFV_DESC "Comics/Viewer"

!define ACBFV_WEBSITE "http://acbf.info"

!define QL_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${ACBFV_NAME}"
!define QL_INSTDIR_KEY "Software\${ACBFV_NAME}"
!define QL_INSTDIR_VALUENAME "InstDir"

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "${ACBFV_NAME} (${VERSION})"
OutFile "acbfv-LATEST.exe"
SetCompressor /SOLID /FINAL lzma
SetCompressorDictSize 32
InstallDir "$PROGRAMFILES\${ACBFV_NAME}"
RequestExecutionLevel admin

Var QL_INST_BIN
Var UNINST_BIN

!define MUI_ABORTWARNING
!define MUI_ICON "acbfv.ico"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"


Section "Install"
    SetShellVarContext all

    ; Use this to make things faster for testing installer changes
    ;~ SetOutPath "$INSTDIR\bin"
    ;~ File /r "mingw32\bin\*.exe"

    SetOutPath "$INSTDIR"
    File /r "mingw32\*.*"

    ; Store installation folder
    WriteRegStr HKLM "${QL_INSTDIR_KEY}" "${QL_INSTDIR_VALUENAME}" $INSTDIR

    ; Set up an entry for the uninstaller
    WriteRegStr HKLM "${QL_UNINST_KEY}" \
        "DisplayName" "${ACBFV_NAME} - ${ACBFV_DESC}"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "DisplayIcon" "$\"$QL_INST_BIN$\""
    WriteRegStr HKLM "${QL_UNINST_KEY}" "UninstallString" \
        "$\"$UNINST_BIN$\""
    WriteRegStr HKLM "${QL_UNINST_KEY}" "QuietUninstallString" \
    "$\"$UNINST_BIN$\" /S"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "HelpLink" "${ACBFV_WEBSITE}"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "Publisher" "ACBF Development Team"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "NoModify" 0x1
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "NoRepair" 0x1
    ; Installation size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "EstimatedSize" "$0"

    ; Register a default entry for file extensions
    WriteRegStr HKLM "Software\Classes\${ACBFV_ID}.assoc.ANY\shell\play\command" "" "$\"$QL_INST_BIN$\" --run --play-file $\"%1$\""
    WriteRegStr HKLM "Software\Classes\${ACBFV_ID}.assoc.ANY\DefaultIcon" "" "$\"$QL_INST_BIN$\""
    WriteRegStr HKLM "Software\Classes\${ACBFV_ID}.assoc.ANY\shell\play" "FriendlyAppName" "${ACBFV_NAME}"

    ; Add application entry
    WriteRegStr HKLM "Software\${ACBFV_NAME}\${ACBFV_ID}\Capabilities" "ApplicationDescription" "${ACBFV_DESC}"
    WriteRegStr HKLM "Software\${ACBFV_NAME}\${ACBFV_ID}\Capabilities" "ApplicationName" "${ACBFV_NAME}"

    ; Register supported file extensions
    ; (generated using gen_supported_types.py)
    !define QL_ASSOC_KEY "Software\${ACBFV_NAME}\${ACBFV_ID}\Capabilities\FileAssociations"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".acbf" "${ACBFV_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".cbz" "${ACBFV_ID}.assoc.ANY"

    ; Register application entry
    WriteRegStr HKLM "Software\RegisteredApplications" "${ACBFV_NAME}" "Software\${ACBFV_NAME}\${ACBFV_ID}\Capabilities"

    ; Register app paths
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\acbfv.exe" "" "$QL_INST_BIN"

    ; Create uninstaller
    WriteUninstaller "$UNINST_BIN"

    ; Create start menu shortcuts
    CreateDirectory "$SMPROGRAMS\${ACBFV_NAME}"
    CreateShortCut "$SMPROGRAMS\${ACBFV_NAME}\${ACBFV_NAME}.lnk" "$QL_INST_BIN"
SectionEnd

Function .onInit
    ; Read the install dir and set it
    Var /GLOBAL instdir_temp
    ReadRegStr $instdir_temp HKLM "${QL_INSTDIR_KEY}" "${QL_INSTDIR_VALUENAME}"
    StrCmp $instdir_temp "" skip 0
        StrCpy $INSTDIR $instdir_temp
    skip:

    StrCpy $QL_INST_BIN "$INSTDIR\bin\acbfv.exe"
    StrCpy $UNINST_BIN "$INSTDIR\uninstall.exe"

    ; try to un-install existing installations first
    IfFileExists "$INSTDIR" do_uninst do_continue
    do_uninst:
        ; instdir exists
        IfFileExists "$UNINST_BIN" exec_uninst rm_instdir
        exec_uninst:
            ; uninstall.exe exists, execute it and
            ; if it returns success proceede, otherwise abort the
            ; installer (uninstall aborted by user for example)
            ExecWait '"$UNINST_BIN" _?=$INSTDIR' $R1
            ; uninstall suceeded, since the uninstall.exe is still there
            ; goto rm_instdir as well
            StrCmp $R1 0 rm_instdir
            ; uninstall failed
            Abort
        rm_instdir:
            ; either the uninstaller was sucessfull or
            ; the uninstaller.exe wasn't found
            RMDir /r "$INSTDIR"
    do_continue:
        ; the instdir shouldn't exist from here on
FunctionEnd

Section "Uninstall"
    SetShellVarContext all
    SetAutoClose true

    ; Remove start menu entries
    Delete "$SMPROGRAMS\${ACBFV_NAME}\${ACBFV_NAME}.lnk"
    RMDir "$SMPROGRAMS\${ACBFV_NAME}"

    ; Remove application registration and file assocs
    DeleteRegKey HKLM "Software\Classes\${ACBFV_ID}.assoc.ANY"
    DeleteRegKey HKLM "Software\${ACBFV_NAME}"
    DeleteRegValue HKLM "Software\RegisteredApplications" "${ACBFV_NAME}"

    ; Remove app paths
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\acbfv.exe"

    ; Delete installation related keys
    DeleteRegKey HKLM "${QL_UNINST_KEY}"
    DeleteRegKey HKLM "${QL_INSTDIR_KEY}"

    ; Delete files
    RMDir /r "$INSTDIR"
SectionEnd
