param([Parameter(Mandatory=$true)][string]$Marker)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class FlashGuardWindow {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
}
'@
$root = [System.Windows.Automation.AutomationElement]::RootElement
$windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
$tabCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::TabItem)
foreach ($window in $windows) {
    try {
        $class = $window.Current.ClassName
        if ($class -ne 'Chrome_WidgetWin_1' -and $class -ne 'MozillaWindowClass') { continue }
        $handle = [IntPtr]$window.Current.NativeWindowHandle
        # Restore minimized windows so their accessible tab strip can be queried.
        # Only restore the matching window after finding its tab; an active tab's title also matches.
        if ($window.Current.Name.Contains($Marker)) {
            [void][FlashGuardWindow]::ShowWindow($handle,9)
            [void][FlashGuardWindow]::SetForegroundWindow($handle)
            exit 0
        }
        $tabs = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tabCondition)
        foreach ($tab in $tabs) {
            if ($tab.Current.Name.Contains($Marker)) {
                [void][FlashGuardWindow]::ShowWindow($handle,9)
                $selection = $null
                $invoke = $null
                if ($tab.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$selection)) {
                    $selection.Select()
                } elseif ($tab.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)) {
                    $invoke.Invoke()
                } else { $tab.SetFocus() }
                [void][FlashGuardWindow]::SetForegroundWindow($handle)
                exit 0
            }
        }
    } catch { continue }
}
exit 1
