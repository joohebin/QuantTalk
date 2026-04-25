$commands = '["find / -name quanttalk.db -o -name main.py -type f 2>/dev/null | head -10","ls -la /root/ 2>/dev/null | head -20","ls /home/ 2>/dev/null","which python3 && python3 --version"]'
$r = aws ssm send-command --document-name AWS-RunShellScript --instance-ids i-03c6b37fd18bcf9b4 --region ap-northeast-1 --parameters "{\"commands\":$commands}" --output json 2>&1
Write-Host "Result length: $($r.Length)"
$r | ConvertFrom-Json | ConvertTo-Json -Depth 5
