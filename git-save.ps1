param(
    [string]$Message = ""
)

Write-Host "========================================"
Write-Host " SALVAR ALTERACOES NO GITHUB"
Write-Host "========================================"

# Garante que estamos na pasta do script
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "Pasta atual:"
Get-Location

Write-Host ""
Write-Host "Verificando branch atual..."
$branch = git branch --show-current

if (-not $branch) {
    Write-Host "ERRO: Esta pasta nao parece ser um repositorio Git." -ForegroundColor Red
    exit 1
}

Write-Host "Branch atual: $branch"

Write-Host ""
Write-Host "Verificando arquivos sensiveis..."

# Garante que .env nao seja enviado
if (Test-Path ".env") {
    git rm --cached .env 2>$null
}

# Garante que generated_projects nao seja enviado, se estiver no .gitignore
if (Test-Path "generated_projects") {
    git rm -r --cached generated_projects 2>$null
}

Write-Host ""
Write-Host "Status atual:"
git status

Write-Host ""
Write-Host "Adicionando alteracoes..."
git add .

Write-Host ""
Write-Host "Status apos git add:"
git status

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = Read-Host "Digite a mensagem do commit"
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "Update project changes"
}

Write-Host ""
Write-Host "Criando commit..."
git commit -m "$Message"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Nenhum commit criado. Pode nao haver alteracoes novas." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Enviando para o GitHub..."
git push origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Alteracoes enviadas com sucesso para o GitHub!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "ERRO ao enviar para o GitHub." -ForegroundColor Red
    Write-Host "Verifique a mensagem acima."
    exit 1
}