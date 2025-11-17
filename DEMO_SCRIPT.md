# Loom Video Demo Script

## Target Audience
A potential customer who isn't familiar with Devin but has a GitHub repository with issues.

## Duration
~5 minutes

---

## Script

### [0:00-0:30] Introduction - The Problem

> "Hi! I'm going to show you something that's going to change how you handle GitHub issues. If you're like most engineering teams, you probably have dozens or even hundreds of open issues in your repositories. Some are bugs, some are feature requests, and they just keep piling up."

> "The problem is: which ones should you work on? How complex are they? And who has time to even assess them all before diving in?"

> "That's where **Devin GitHub Issues Automation** comes in. Let me show you what it does."

---

### [0:30-1:00] Solution Overview

> "This is a CLI tool I built that integrates Devin AI with your GitHub issues. It gives you three superpowers:"

**Show the README or a simple diagram while saying:**

> "First, you can **list and filter** all your issues to see what's open."

> "Second, you can ask Devin to **scope** any issue - it'll analyze the issue, create an implementation plan, assess the risk, and give you a confidence score on whether it can actually solve it."

> "And third, if you like the plan, you can tell Devin to **execute** - and it will actually implement the fix, run tests, and open a pull request for you. Completely automatically."

> "Let me show you how this works in practice."

---

### [1:00-1:30] Feature 1: List Issues

**Open terminal, show:**

```bash
python devin-issues list owner/repo --label bug --state open
```

> "First, I'm going to list all the open bugs in my repository. As you can see, we get a nice table showing all the issues, their titles, labels, and when they were last updated."

> "Now let's pick one to work on. I'm going to choose issue #5 here - it's about adding an admin dashboard."

---

### [1:30-3:00] Feature 2: Scope the Issue

**Run the scope command:**

```bash
python devin-issues scope owner/repo 5 --wait
```

> "Now I'm going to ask Devin to scope this issue. This is where the magic happens."

> "Devin is reading the issue description, all the comments, understanding the context, and creating an implementation plan. This usually takes 2-3 minutes."

**While waiting, explain:**

> "What's cool is Devin isn't just saying 'yes I can do this' - it's actually thinking through HOW it would do it. It's looking at the codebase, understanding the architecture, and planning out the steps."

**When results appear:**

> "Okay, look at this! Devin has given us:"

> "**First**, a clear summary of what needs to be done - add an admin dashboard with role-based authorization to delete profiles."

> "**Second**, a step-by-step implementation plan - you can see it's broken down into 6 specific steps, from adding an admin role field to the database, to creating the UI, to implementing delete actions."

> "**Third**, a risk assessment - it's saying this is 'medium' risk, which makes sense since we're dealing with data deletion."

> "**Fourth**, an effort estimate - 8 hours of work."

> "And **most importantly**, a confidence score - 80%. Devin is 80% confident it can successfully implement this."

> "This is incredibly valuable because I can now decide: is this worth having Devin work on, or should a human handle this? With 80% confidence and a clear plan, I'm comfortable letting Devin proceed."

---

### [3:00-4:00] Feature 3: Execute the Issue

**Run the execute command:**

```bash
python devin-issues execute owner/repo 5
```

> "Now I'm going to tell Devin to actually implement this. I'm not using the --wait flag because this will take 15-20 minutes, but let me show you what happens."

> "You can see it's created a Devin session, and we get a URL to watch Devin work in real-time. Devin is now:"

> "- Creating a feature branch"
> "- Writing the actual code following that plan we just saw"
> "- Running tests to make sure nothing breaks"  
> "- And it will open a pull request when it's done"

> "The really cool part? While this is happening, Devin automatically posts updates to the GitHub issue, so the person who filed it knows it's being worked on."

---

### [4:00-4:30] Feature 4: Status Monitoring

**Show the status command:**

```bash
python devin-issues status
```

> "And if I want to check on progress, I can use the status command. This shows me all my active Devin sessions - what they're working on, what phase they're in, whether they're running or finished."

**Show specific session:**

```bash
python devin-issues status SESSION_ID
```

> "And I can drill down into any specific session to see the structured output - what branch was created, whether tests passed, and the pull request URL once it's ready."

---

### [4:30-4:50] Show the Results

**Switch to GitHub, show:**

> "And here's the final result - Devin has opened a pull request with all the changes. The code is here, the tests are passing, and I can review it just like I would with any other PR."

> "If it looks good, I merge it. If Devin made a mistake, I can give it feedback and it can fix it. But the point is: I went from 'there's an issue' to 'there's a complete implementation ready to review' without writing a single line of code myself."

---

### [4:50-5:00] Closing - The Value Proposition

> "So let me recap what this gives you:"

> "**One**: Instant triage - you know which issues are automatable and which need human attention."

> "**Two**: Time savings - issues that would take your team hours or days can be scoped in minutes and implemented in under an hour."

> "**Three**: Consistency - every issue gets the same thorough analysis and implementation quality."

> "This isn't about replacing your engineers - it's about freeing them up to work on the complex, creative problems that actually need human insight, while Devin handles the routine fixes and features."

> "Thanks for watching! If you want to try this on your own repository, all the code is on GitHub. Let me know what you think!"

---

## Tips for Recording

### Before You Start
1. ✅ Have a real GitHub repository with actual issues ready
2. ✅ Make sure backend is running (`uvicorn app.api.main:app`)
3. ✅ Test run all commands beforehand
4. ✅ Have at least one completed Devin session to show real results
5. ✅ Open the Devin session URL in a browser tab (to show it working)
6. ✅ Have a completed PR open in GitHub to show the end result

### During Recording
1. ✅ **Keep it conversational** - you're showing this to a customer, not giving a technical deep-dive
2. ✅ **Focus on value** - always tie features back to "why does this matter?"
3. ✅ **Show real results** - don't fake the demo, show an actual PR Devin created
4. ✅ **Pace yourself** - don't rush, but stay within 5 minutes
5. ✅ **Show enthusiasm** - this is genuinely cool technology!

### What to Show on Screen
- **Mostly**: Terminal with CLI commands
- **Sometimes**: GitHub UI showing issues and PRs
- **Briefly**: Devin session URL (the actual Devin interface working)
- **End with**: A real merged PR that Devin created

### What NOT to Do
- ❌ Don't show code editors or explain implementation details
- ❌ Don't show errors or things not working (test beforehand!)
- ❌ Don't use technical jargon (assume the audience is non-technical)
- ❌ Don't go over 5 minutes (edit it down if needed)
- ❌ Don't show your API keys or tokens

### Backup Plan
If Devin is taking too long during recording:
- Use a pre-recorded session for the scope/execute parts
- Jump to the results immediately
- Say "I'm going to skip ahead to when Devin finished..."

---

## Example Repositories to Demo

### Good Choices
- Your own project with real issues
- A small open-source project you maintain
- A demo project you created specifically for this

### What Makes a Good Demo Issue
✅ Clear description
✅ Not too trivial (shows Devin's power)
✅ Not too complex (Devin can actually solve it)
✅ Something a customer can relate to (bug fix, feature add, UI improvement)

### Suggested Demo Issues
1. "Add dark mode toggle" - relatable, visual, clear scope
2. "Fix login error for special characters" - bug fix everyone understands
3. "Add export to CSV feature" - common feature request
4. "Improve error messages in checkout flow" - UX improvement

---

## Key Messages to Emphasize

### For Engineering Managers
> "This lets your team focus on architecture and innovation, not routine fixes."

### For Solo Developers  
> "This is like having a junior developer who never gets tired and works 24/7."

### For Product Teams
> "Issues get resolved faster, which means features ship faster."

### For Everyone
> "You don't need to be a Devin expert to use this - it's just a simple command line tool."

---

## After Recording Checklist

✅ Watch it back - does it flow well?
✅ Is it under 5 minutes?
✅ Did you show a complete end-to-end flow?
✅ Would someone who doesn't know Devin understand it?
✅ Did you show real results (actual PR)?
✅ Is the audio clear?
✅ Are there any dead spots or long waits? (edit them out)
✅ Did you blur/hide any sensitive information?

---

## File This With Your Deliverables

When submitting, include:
1. ✅ Link to this GitHub repository
2. ✅ Link to your Loom video
3. ✅ Brief README explaining how to set it up

**Good luck with your demo! You've built something really impressive. 🚀**

