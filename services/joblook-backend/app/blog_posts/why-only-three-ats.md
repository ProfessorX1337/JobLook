---
title: "Why JobLook only supports three ATSes"
author: "Alex Rivera"
author_title: "Founder, JobLook"
date: "2026-03-20"
category: "Product Updates"
tags: "product, ats, greenhouse, lever, ashby, engineering"
published: true
---

The most common feedback we get is: "can you support Workday? iCIMS? Taleo? Lever Legacy? The one my dream company uses?"

The honest answer is: not yet, and here's the reasoning we use to decide.

## The math of a bad adapter

We could ship an adapter for every major ATS tomorrow. Most of them are technically solvable. The problem is that "technically solvable" and "reliable enough to ship" are very different things.

Greenhouse, Lever, and Ashby share three properties that make them autofillable:

1. **Stable form structure.** The DOM on a Greenhouse application didn't change meaningfully between the job you applied to last month and the one you'll apply to next week.
2. **Predictable field labels.** When a field is labeled "first name", it's labeled "first name" — not "given name (required, as on government-issued ID)" with three nested shadow DOMs.
3. **Honest HTML inputs.** When you type into a field, the framework updates the value. You don't have to simulate a React synthetic event just to get the form to believe something happened.

Workday breaks all three. iCIMS breaks two. Older Taleo deployments are essentially unique to every customer who deployed them.

## What "supporting" an ATS actually means

It is not: "we wrote code that mostly works against one test page we found."

It is: "we wrote an adapter, we tested it against fifty live job postings from companies in our user base, we wrote end-to-end tests that replay real DOM snapshots, we know what breaks when the ATS changes their markup, and we have a plan to fix it within forty-eight hours when they do."

The second bar is ten times the work of the first. That is why our adapter count grows slowly.

## What this means for you

If the company you want is on Greenhouse, Lever, or Ashby — which covers the majority of tech, startup, and growth-stage hiring — JobLook fills the form. If the company is on Workday, you fill it by hand.

We will not ship a Workday adapter that works on half the postings, breaks on the other half, and silently corrupts your application on ten percent of submissions. We watched a competitor do that in 2024. Their users got rejected from roles and never knew why.

## What's next

Workday is genuinely hard and the one most of you ask for. We have a prototype. When it's reliable we'll ship it. Until then, we'd rather be excellent at three ATSes than mediocre at seven.

If you care about a specific ATS we don't support, tell us which one and which companies you're targeting. That is how we prioritize.

*— Alex*
