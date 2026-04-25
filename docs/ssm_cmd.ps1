$params = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @("i-03c6b37fd18bcf9b4")
    Region = "ap-northeast-1"
    Parameters = @{
        commands = @(
            "find / -name 'main.py' -type f 2>/dev/null | head -10",
            "ls -la /root/ 2>/dev/null | head -20",
            "ls -la /home/ubuntu/ 2>/dev/null | head -20"
        )
    }
}

$result = aws ssm send-command @params --output json 2>&1
Write-Host $result

if ($result -match '"CommandId":\s*"([^"]+)"') {
    $cmdId = $matches[1]
    Write-Host "Command ID: $cmdId"
    Start-Sleep -Seconds 5
    $invResult = aws ssm get-command-invocation --command-id $cmdId --instance-id i-03c6b37fd18bcf9b4 --region ap-northeast-1 --output json 2>&1
    Write-Host $invResult
}
