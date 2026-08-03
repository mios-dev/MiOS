@{
    IncludeDefaultRules = $true
    Severity = @('Error')
    Rules = @{
        PSAvoidUsingInvokeExpression = @{
            Enable = $true
            Severity = 'Error'
        }
        PSAvoidUsingPlainTextForPassword = @{
            Enable = $true
            Severity = 'Error'
        }
        PSAvoidAssignmentToAutomaticVariable = @{
            Enable = $true
            Severity = 'Error'
        }
        PSUseDeclaredVarsMoreThanAssignments = @{
            Enable = $true
            Severity = 'Warning'
        }
        PSUseShouldProcessForStateChangingFunctions = @{
            Enable = $true
            Severity = 'Warning'
        }
    }
}
