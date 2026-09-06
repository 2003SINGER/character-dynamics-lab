param(
    [Parameter(Mandatory=$true)][string]$ReplayPath,
    [string]$BuildDir = "build\character-dynamics",
    [string]$OutputDir = "outputs\experiments\LIGHT_compiled_semantics_v0",
    [int]$MaxTrajectories = 50,
    [int]$CounterfactualTrajectories = 20
)
$ErrorActionPreference = "Stop"
$Rules = "02_实验\T0c_LIGHT\compiled_semantics_v0.json"
$Runner = "02_实验\T0c_LIGHT\run_compiled_semantics_v0.py"

Write-Host "=== 1 configure ==="
cmake -S "Demo codex-generated" -B $BuildDir

Write-Host "=== 2 build ==="
cmake --build $BuildDir --config Release

Write-Host "=== 3 CTest ==="
ctest --test-dir $BuildDir -C Release --output-on-failure

Write-Host "=== 4 ReplayRecord validator ==="
py -3 "tools\validate_replay_record.py" $ReplayPath

$Candidates = @(
    (Join-Path $BuildDir "character_dynamics_replay_core.exe"),
    (Join-Path $BuildDir "Release\character_dynamics_replay_core.exe"),
    (Join-Path $BuildDir "character_dynamics_replay_core"),
    (Join-Path $BuildDir "Release\character_dynamics_replay_core")
)
$Core = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Core) { throw "character_dynamics_replay_core not found under $BuildDir" }

Write-Host "=== 5 semantic coverage audit ==="
$Audit = Join-Path $OutputDir "LIGHT_candidate_verb_audit.json"
py -3 "02_实验\T0c_LIGHT\audit_candidate_verbs.py" `
    $ReplayPath $Rules $Audit --max-trajectories $MaxTrajectories

Write-Host "=== 6 factual held-out replay ==="
py -3 $Runner `
    $ReplayPath $Core $OutputDir `
    --rules $Rules --max-trajectories $MaxTrajectories

Write-Host "=== 7 single-event remove counterfactual ==="
$Counter = Join-Path $OutputDir "LIGHT_semantic_update_remove_diagnostic_v0.trace.jsonl"
py -3 "02_实验\T0c_LIGHT\semantic_update_remove_diagnostic_v0.py" `
    $ReplayPath $Core $Counter `
    --rules $Rules --runner $Runner `
    --max-trajectories $CounterfactualTrajectories

Write-Host ""
Write-Host "READY: $OutputDir"
Write-Host "Inspect:"
Write-Host "  LIGHT_candidate_verb_audit.json"
Write-Host "  LIGHT_compiled_semantics_v0.summary.json"
Write-Host "  LIGHT_compiled_semantics_v0.manifest.json"
Write-Host "  LIGHT_compiled_semantics_v0.trace.jsonl"
Write-Host "  LIGHT_semantic_update_remove_diagnostic_v0.trace.jsonl"
