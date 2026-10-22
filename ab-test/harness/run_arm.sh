#!/usr/bin/env bash
# usage: run_arm.sh <dir> <promptfile> [resume]   — runs one A/B arm in its own folder with a fixed tool allow-list
cd "$1"
start=$(date +%s)
extra=()
if [ "$3" = "resume" ]; then extra=(--continue); fi
rm -f run.done
CLAUDE_AUTO_BACKGROUND_TASKS=false timeout 6900 claude -p "$(cat "$2")" "${extra[@]}" --model claude-opus-5-5 --max-turns 600 \
  --allowedTools "Bash Read Write Edit Glob Grep Agent Skill TaskCreate TaskUpdate TaskList TaskGet WebSearch WebFetch ToolSearch SendMessage" \
  --disallowedTools "SendUserFile SendUserMessage Artifact PushNotification ScheduleWakeup CronCreate" \
  --output-format stream-json --verbose < /dev/null >> run.jsonl 2>> run.err
echo "exit=$? seconds=$(( $(date +%s) - start ))" > run.done
