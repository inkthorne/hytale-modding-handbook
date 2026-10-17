#!/usr/bin/env bash
# Test run.sh's scratch guard with a FAKE HOME.   maintenance/probes/beams/guard-test.sh WORKDIR
#
# WORKDIR is a scratch directory (it is wiped). Nothing outside it is touched: HOME is set to
# WORKDIR/home, and the "game" is two empty files, so no server ever starts (an accepted case would
# fail at `java -jar` of an empty file, after the guard).
#
# Negative control first: the run.sh of 584d7d1 (before the guard was rewritten) is pulled out of git
# and must delete the fake save in at least one attack. If it deletes nothing, the attacks prove
# nothing and the test is VOID (exit 2). Then the current run.sh must refuse every attack (exit 3)
# and leave the fake save and the fake .var/app in place, and must still accept a legitimate scratch.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
base="${1:?usage: guard-test.sh WORKDIR}"
case "$base" in /*) ;; *) echo "FAIL  WORKDIR must be absolute" >&2; exit 3;; esac
rm -rf -- "$base"; mkdir -p "$base/game/Server"
: > "$base/game/Server/HytaleServer.jar"; : > "$base/game/Assets.zip"
git -C "$here" show 584d7d1:maintenance/probes/beams/run.sh > "$base/run-old.sh" 2>/dev/null || { echo "FAIL  cannot read the old run.sh from git" >&2; exit 3; }
save() { echo "$base/home/.var/app/x/UserData/Saves/arena/config.json"; }
fresh() { rm -rf "$base/home" "$base/legit"; mkdir -p "$base/home/.var/app/x/UserData/Saves/arena" "$base/legit"; echo keep > "$(save)"; }
survives() { [ -f "$(save)" ] && [ -d "$base/home/.var/app" ]; }

attacks() { # prints "name|result" lines and sets DELETED_ANY / NOT_REFUSED
  local h="$base/home"
  local names=("dot-segment scratch" "scratch is HOME, case .var" "relative scratch" "case with ../")
  fresh; ( cd "$base"; HOME="$h" HYTALE_GAME="$base/game" bash "$RUN" "$h/./.var/app/x/UserData" Saves >/dev/null 2>&1 ); r1=$?; survives && s1=survived || s1=DELETED
  fresh; ( cd "$base"; HOME="$h" HYTALE_GAME="$base/game" bash "$RUN" "$h" .var >/dev/null 2>&1 ); r2=$?; survives && s2=survived || s2=DELETED
  fresh; ( cd "$h"; HOME="$h" HYTALE_GAME="$base/game" bash "$RUN" .var/app/x/UserData Saves >/dev/null 2>&1 ); r3=$?; survives && s3=survived || s3=DELETED
  fresh; ( cd "$base"; HOME="$h" HYTALE_GAME="$base/game" bash "$RUN" "$base/legit" "../home/.var/app/x/UserData/Saves" >/dev/null 2>&1 ); r4=$?; survives && s4=survived || s4=DELETED
  RES=("${names[0]}|$s1|$r1" "${names[1]}|$s2|$r2" "${names[2]}|$s3|$r3" "${names[3]}|$s4|$r4")
}

RUN="$base/run-old.sh"; attacks
deleted=0; for r in "${RES[@]}"; do case "$r" in *"|DELETED|"*) deleted=$((deleted+1));; esac; done
for r in "${RES[@]}"; do echo "old run.sh: $r"; done
if [ "$deleted" = 0 ]; then echo "VOID  the old run.sh deleted nothing in a fake HOME, so these attacks prove nothing"; exit 2; fi
echo "control held: the old run.sh deleted the fake save/.var in $deleted of 4 attacks"

RUN="$here/run.sh"; attacks; fails=0
for r in "${RES[@]}"; do
  IFS='|' read -r n st rc <<< "$r"
  if [ "$st" = survived ] && [ "$rc" = 3 ]; then echo "PASS  $n: refused (rc 3), save survives"; else echo "FAIL  $n: $st rc=$rc"; fails=$((fails+1)); fi
done
# the scratch guard on its own: known case name, bad SCRATCH; the refusal must name the scratch rule
h="$base/home"
scratch_attack() { # label, cwd, scratch, expected message fragment
  fresh; local out; out="$(cd "$2" && HOME="$h" HYTALE_GAME="$base/game" bash "$RUN" "$3" boot 2>&1)"; local rc=$?
  if [ "$rc" = 3 ] && printf '%s' "$out" | /usr/bin/grep -qF "$4" && survives; then echo "PASS  $1: refused with '$4'"; else echo "FAIL  $1: rc=$rc out=$out"; fails=$((fails+1)); fi
}
scratch_attack "dot segment under .var" "$base" "$h/./.var/app/x/UserData" "is inside"
scratch_attack "SCRATCH is HOME" "$base" "$h" 'SCRATCH is $HOME'
scratch_attack "relative SCRATCH" "$h" ".var/app/x/UserData" "must be an absolute path"
fresh; ln -s "$h/.var/app/x/UserData" "$base/link"
scratch_attack "symlink into .var" "$base" "$base/link" "is inside"
# an existing directory that is not ours is not removed, even under a legitimate scratch
fresh; mkdir -p "$base/legit/boot"; echo mine > "$base/legit/boot/precious"
HOME="$base/home" HYTALE_GAME="$base/game" bash "$RUN" "$base/legit" boot >/dev/null 2>&1; rc=$?
if [ -f "$base/legit/boot/precious" ] && [ "$rc" = 3 ]; then echo "PASS  existing unmarked dir SCRATCH/boot: refused, not removed"; else echo "FAIL  unmarked dir: rc=$rc"; fails=$((fails+1)); fi
# the legitimate form is accepted by the guard (it then fails at java -jar of the empty fake jar, rc != 3 from the guard's refusals)
fresh; out="$(HOME="$base/home" HYTALE_GAME="$base/game" bash "$RUN" "$base/legit" boot 2>&1)"
if [ -f "$base/legit/boot/.beams-probe-case" ] && ! printf '%s' "$out" | /usr/bin/grep -q '^FAIL'; then echo "PASS  legitimate scratch and case: accepted, case dir created"; else echo "FAIL  legitimate form refused: $out"; fails=$((fails+1)); fi
# the same run, twice: our own marked dir is replaced
HOME="$base/home" HYTALE_GAME="$base/game" bash "$RUN" "$base/legit" boot >/dev/null 2>&1
[ -f "$base/legit/boot/.beams-probe-case" ] && echo "PASS  a marked case dir is replaced by a re-run" || { echo "FAIL  re-run"; fails=$((fails+1)); }
echo "---- $fails failed"
[ "$fails" = 0 ]
