Title: This Week in Rust 582
Number: 582
Date: 2025-01-15
Category: This Week in Rust

Hello and welcome to another issue of *This Week in Rust*!
[Rust](https://www.rust-lang.org/) is a programming language empowering everyone to build reliable and efficient software.
This is a weekly summary of its progress and community.
Want something mentioned? Tag us at [@ThisWeekInRust](https://x.com/ThisWeekInRust) on X (formerly Twitter) or [@ThisWeekinRust](https://mastodon.social/@thisweekinrust) on mastodon.social, or [send us a pull request](https://github.com/rust-lang/this-week-in-rust).
Want to get involved? [We love contributions](https://github.com/rust-lang/rust/blob/master/CONTRIBUTING.md).

*This Week in Rust* is openly developed [on GitHub](https://github.com/rust-lang/this-week-in-rust) and archives can be viewed at [this-week-in-rust.org](https://this-week-in-rust.org/).
If you find any errors in this week's issue, [please submit a PR](https://github.com/rust-lang/this-week-in-rust/pulls).

Want TWIR in your inbox? [Subscribe here](https://this-week-in-rust.us11.list-manage.com/subscribe?u=fd84c1c757e02889a9b08d289&id=0ed8b72485).

## Updates from Rust Community

<!--

Dear community contributors:
Please read README.md for guidance on submissions.
Each submitted link should be of the form:

* [Title of the Linked Page](https://example.com/my_article)

If you don't know which category to use, feel free to submit a PR anyway
and just ask the editors to select the category.

-->

### Official
* [Announcing Rust 1.84.0](https://blog.rust-lang.org/2025/01/09/Rust-1.84.0.html)
* [This Month in Our Test Infra: December 2024](https://blog.rust-lang.org/inside-rust/2025/01/10/test-infra-dec-2024.html)

### Foundation
* [Announcing Rust Global 2025: London](https://foundation.rust-lang.org/news/announcing-rust-global-2025-london/)

### Newsletters
* [This Month in Rust OSDev: December 2024](https://rust-osdev.com/this-month/2024-12/)
* [Rust Trends Issue #57](https://rust-trends.com/newsletter/start-2025-with-rust-honeypots-free-cloud-deployments-and-software-reliability/)

### Project/Tooling Updates
* [cargo.nvim - A Neovim plugin for Rust's Cargo commands](https://github.com/nwiizo/cargo.nvim)
* [Context-Generic Programming Updates: v0.3.0 Release and New Chapters](https://contextgeneric.dev/blog/v0-3-0-release/)
* [The RTen machine learning runtime - a 2024 retrospective](https://robertknight.me.uk/posts/rten-2024/)

### Observations/Thoughts
* [The gen auto-trait problem](https://blog.yoshuawuyts.com/gen-auto-trait-problem/)
* [Async Rust is about concurrency, not (just) performance](https://kobzol.github.io/rust/2025/01/15/async-rust-is-about-concurrency.html)
* [The Emotional Appeal of Rust](https://www.shuttle.dev/blog/2025/01/14/the-appeal-of-rust)
* [audio] [Brave with Anton Lazarev](https://corrode.dev/podcast/s03e07-brave/)
* [audio] [Lychee with Matthias Endler](https://rustacean-station.org/episode/matthias-endler/)

### Rust Walkthroughs
* [Creating an embedded device driver in Rust](https://blog.mjolner.tech/device-driver-rust/)
* [Const Evaluation in Rust For Hex Strings Validation](https://asyncmove.com/blog/2025/01/compile-time-hex-string-validation-in-rust-using-const-evaluation/)
* [Concurrent and parallel future execution in Rust](https://heikoseeberger.de/2025-01-15-concurrent-parallel-futures/)
* [video] [Intro to Embassy: embedded development with async Rust](https://www.youtube.com/watch?v=pDd5mXBF4tY)
* [video] [Comprehending Proc Macros](https://www.youtube.com/watch?v=SMCRQj9Hbx8)
* [video] [CppCon - C++/Rust Interop: Using Bridges in Practice](https://tylerjw.dev/posts/20240920-cppcon-cpp-rust-interop/)

### Miscellaneous
* [December 2024 Rust Jobs Report](https://filtra.io/rust/jobs-report/dec-24)
* [Tracing Large Memory Allocations in Rust with BPFtrace](https://readyset.io/blog/tracing-large-memory-allocations-in-rust-with-bpftrace)
* [On LLMs and Code Optimization](https://wiredream.com/llm-optimizing-digit-diff/)
* [Nand2Tetris - Project 7 (VM Translator Part 1)](https://gurudas.dev/blog/2025/01/01/nand-to-tetris-2024-project-7/)

## Crate of the Week

This week's crate is [vidyut](https://github.com/ambuda-org/vidyut), a Sanskrit toolkit containing functionality about meter, segmentation, inflections, etc.

Thanks to [Arun Prasad](https://users.rust-lang.org/t/crate-of-the-week/2704/1387) for the self-suggestion!

[Please submit your suggestions and votes for next week][submit_crate]!

[submit_crate]: https://users.rust-lang.org/t/crate-of-the-week/2704

## Calls for Testing
An important step for RFC implementation is for people to experiment with the
implementation and give feedback, especially before stabilization.  The following
RFCs would benefit from user testing before moving forward:

### [RFCs](https://github.com/rust-lang/rfcs/issues?q=label%3Acall-for-testing)
* *No calls for testing were issued this week.*

### [Rust](https://github.com/rust-lang/rust/labels/call-for-testing)
* [Tracking issue for RFC 3695: Allow boolean literals as cfg predicates](https://github.com/rust-lang/rust/issues/131204)
  - [Testing steps](https://github.com/rust-lang/rust/issues/131204#issuecomment-2569314526)

### [Rustup](https://github.com/rust-lang/rustup/labels/call-for-testing)
* *No calls for testing were issued this week.*

If you are a feature implementer and would like your RFC to appear on the above list, add the new `call-for-testing`
label to your RFC along with a comment providing testing instructions and/or guidance on which aspect(s) of the feature
need testing.

### [RFCs](https://github.com/rust-lang/rfcs/issues?q=label%3Acall-for-testing)

### [Rust](https://github.com/rust-lang/rust/labels/call-for-testing)

### [Rustup](https://github.com/rust-lang/rustup/labels/call-for-testing)

If you are a feature implementer and would like your RFC to appear on the above list, add the new `call-for-testing`
label to your RFC along with a comment providing testing instructions and/or guidance on which aspect(s) of the feature
need testing.

## Call for Participation; projects and speakers

### CFP - Projects

Always wanted to contribute to open-source projects but did not know where to start?
Every week we highlight some tasks from the Rust community for you to pick and get started!

Some of these tasks may also have mentors available, visit the task page for more information.

<!-- CFPs go here, use this format: * [project name - title of issue](URL to issue) -->
<!-- * [ - ]() -->
<!-- or if none - *No Calls for participation were submitted this week.* -->

* [rama - see if improvements can/have-to be made to rama's http open telemetry layer support](https://github.com/plabayo/rama/issues/383)
* [rama – add rama to TechEmpower's FrameworkBenchmark](https://github.com/plabayo/rama/issues/389)
* [rama – add rama server benchmark to sharkbench](https://github.com/plabayo/rama/issues/390)

If you are a Rust project owner and are looking for contributors, please submit tasks [here][guidelines] or through a [PR to TWiR](https://github.com/rust-lang/this-week-in-rust) or by reaching out on [X (formerly Twitter)](https://x.com/ThisWeekInRust) or [Mastodon](https://mastodon.social/@thisweekinrust)!

[guidelines]:https://github.com/rust-lang/this-week-in-rust?tab=readme-ov-file#call-for-participation-guidelines

### CFP - Events

Are you a new or experienced speaker looking for a place to share something cool? This section highlights events that are being planned and are accepting submissions to join their event as a speaker.

<!-- CFPs go here, use this format: * [**event name**](URL to CFP)| Date CFP closes in YYYY-MM-DD | city,state,country | Date of event in YYYY-MM-DD -->
<!-- or if none - *No Calls for papers or presentations were submitted this week.* -->

* [**Rust Week (Rust NL)**](https://www.papercall.io/rust-week) | Closes on 2025-01-19 | Utrecht, NL | Event on 2025-05-13 & 2025-05-14
* [**Rust Summit**](https://docs.google.com/forms/d/e/1FAIpQLSf_O5ISyLQm_DL5_pEcMkc6AWMp7t4YufO-7kwUQTGQ5MW4dw/viewform) | Rolling deadline | Belgrade, RS | Event on 2025-06-07

If you are an event organizer hoping to expand the reach of your event, please submit a link to the website through a [PR to TWiR](https://github.com/rust-lang/this-week-in-rust) or by reaching out on [X (formerly Twitter)](https://x.com/ThisWeekInRust) or [Mastodon](https://mastodon.social/@thisweekinrust)!

## Updates from the Rust Project

469 pull requests were [merged in the last week][merged]

[merged]: https://github.com/search?q=is%3Apr+org%3Arust-lang+is%3Amerged+merged%3A2025-01-07..2025-01-14

* [add new `{x86_64,i686}-win7-windows-gnu` targets](https://github.com/rust-lang/rust/pull/134609)
* [arm: add unstable soft-float target feature](https://github.com/rust-lang/rust/pull/135203)
* [`-Zrandomize-layout` harder. `Foo<T> != Foo<U>`](https://github.com/rust-lang/rust/pull/133088)
* [`best_blame_constraint`: Blame better constraints when the region graph has cycles from invariance or `'static`](https://github.com/rust-lang/rust/pull/133858)
* [`mir_transform`: implement `#[rustc_force_inline]`](https://github.com/rust-lang/rust/pull/134082)
* [`run_make_support`: add `#![warn(unreachable_pub)]`](https://github.com/rust-lang/rust/pull/135411)
* [account for identity substituted items in symbol mangling](https://github.com/rust-lang/rust/pull/135261)
* [add `-Zmin-function-alignment`](https://github.com/rust-lang/rust/pull/134030)
* [add `default_field_values` entry to unstable book](https://github.com/rust-lang/rust/pull/134855)
* [add a list of symbols for stable standard library crates](https://github.com/rust-lang/rust/pull/135247)
* [add an `InstSimplify` for repetitive array expressions](https://github.com/rust-lang/rust/pull/135274)
* [add inherent versions of `MaybeUninit` methods for slices](https://github.com/rust-lang/rust/pull/129259)
* [add missing provenance APIs on `NonNull`](https://github.com/rust-lang/rust/pull/135242)
* [assert that `Instance::try_resolve` is only used on body-like things](https://github.com/rust-lang/rust/pull/135426)
* [avoid ICE: Account for `for<'a>` types when checking for non-structural type in constant as pattern](https://github.com/rust-lang/rust/pull/134776)
* [avoid replacing the definition of `CURRENT_RUSTC_VERSION`](https://github.com/rust-lang/rust/pull/135173)
* [cleanup `suggest_binding_for_closure_capture_self` diag in borrowck](https://github.com/rust-lang/rust/pull/135364)
* [condvar: implement `wait_timeout` for targets without threads](https://github.com/rust-lang/rust/pull/134389)
* [convert typeck constraints in location-sensitive polonius](https://github.com/rust-lang/rust/pull/134920)
* [depth limit const eval query](https://github.com/rust-lang/rust/pull/135167)
* [detect `mut arg: &Ty` meant to be `arg: &mut Ty` and provide structured suggestion](https://github.com/rust-lang/rust/pull/134977)
* [do not ICE when encountering predicates from other items in method error reporting](https://github.com/rust-lang/rust/pull/135083)
* [eagerly collect mono items for non-generic closures](https://github.com/rust-lang/rust/pull/135314)
* [ensure that we don't try to access fields on a non-struct pattern type](https://github.com/rust-lang/rust/pull/135222)
* [exhaustively handle expressions in patterns](https://github.com/rust-lang/rust/pull/134228)
* [fix ICE with references to infinite structs in consts](https://github.com/rust-lang/rust/pull/135464)
* [fix cycle error only occurring with -Zdump-mir](https://github.com/rust-lang/rust/pull/134498)
* [fix handling of ZST in win64 ABI on windows-msvc targets](https://github.com/rust-lang/rust/pull/135204)
* [implement `const Destruct` in old solver](https://github.com/rust-lang/rust/pull/134875)
* [lower Guard Patterns to HIR](https://github.com/rust-lang/rust/pull/134989)
* [make (unstable API) `UniqueRc` invariant for soundness](https://github.com/rust-lang/rust/pull/135379)
* [make MIR cleanup for functions with impossible predicates into a real MIR pass](https://github.com/rust-lang/rust/pull/135377)
* [make `lit_to_mir_constant` and `lit_to_const` infallible](https://github.com/rust-lang/rust/pull/135195)
* [normalize each signature input/output in `typeck_with_fallback` with its own span](https://github.com/rust-lang/rust/pull/134745)
* [remove a bunch of diagnostic stashing that doesn't do anything](https://github.com/rust-lang/rust/pull/135378)
* [remove allocations from case-insensitive comparison to keywords](https://github.com/rust-lang/rust/pull/135371)
* [remove special-casing for argument patterns in MIR typeck (attempt to fix perf regression of #133858)](https://github.com/rust-lang/rust/pull/135273)
* [reserve x18 register for aarch64 wrs vxworks target](https://github.com/rust-lang/rust/pull/135184)
* [rm unnecessary `OpaqueTypeDecl` wrapper](https://github.com/rust-lang/rust/pull/135440)
* [suggest Replacing Comma with Semicolon in Incorrect Repeat Expressions](https://github.com/rust-lang/rust/pull/128110)
* [support target specific `optimized-compiler-builtins`](https://github.com/rust-lang/rust/pull/135326)
* [unify conditional-const error reporting with non-const error reporting](https://github.com/rust-lang/rust/pull/134732)
* [use a post-monomorphization typing env when mangling components that come from impls](https://github.com/rust-lang/rust/pull/135149)
* [use llvm.memset.p0i8.* to initialize all same-bytes arrays](https://github.com/rust-lang/rust/pull/135258)
* [used pthread name functions returning result for FreeBSD and DragonFly](https://github.com/rust-lang/rust/pull/132607)
* [warn about broken simd not only on structs but also enums and unions when we didn't opt in to it](https://github.com/rust-lang/rust/pull/135219)
* [implement trait upcasting](https://github.com/rust-lang/chalk/pull/821)
* [mir-opt: GVN some more transmute cases](https://github.com/rust-lang/rust/pull/133324)
* [miri: add FreeBSD maintainer; test all of Solarish](https://github.com/rust-lang/miri/pull/4135)
* [miri: added Android to `epoll` and `eventfd` test targets](https://github.com/rust-lang/miri/pull/4137)
* [miri: adjust the way we build miri-script in RA, to fix proc-macros](https://github.com/rust-lang/miri/pull/4134)
* [miri: illumos: added epoll and eventfd](https://github.com/rust-lang/miri/pull/4136)
* [miri: supported fioclex for ioctl on macos](https://github.com/rust-lang/miri/pull/4133)
* [miri: switched FreeBSD to `pthread_setname_np`](https://github.com/rust-lang/miri/pull/4132)
* [miri: use `deref_poiner_as` instead of `deref_pointer`](https://github.com/rust-lang/miri/pull/4138)
* [`proc_macro`: Use `ToTokens` trait in `quote` macro](https://github.com/rust-lang/rust/pull/134693)
* [add `#[inline]` to `copy_from_slice`](https://github.com/rust-lang/rust/pull/135384)
* [impl `String::into_chars`](https://github.com/rust-lang/rust/pull/133057)
* [initial fs module for uefi](https://github.com/rust-lang/rust/pull/135324)
* [hashbrown: added Allocator template argument for `rustc_iter`](https://github.com/rust-lang/hashbrown/pull/605)
* [account for optimization levels other than numbers](https://github.com/rust-lang/compiler-builtins/pull/743)
* [cargo: schemas: Fix 'metadata' JSON Schema](https://github.com/rust-lang/cargo/pull/15033)
* [cargo: schemas: Fix the `[lints]` JSON Schema](https://github.com/rust-lang/cargo/pull/15035)
* [cargo: perf: cargo-package: match certain path prefix with pathspec](https://github.com/rust-lang/cargo/pull/14997)
* [cargo: fix: emit warnings as warnings when learning rust target info](https://github.com/rust-lang/cargo/pull/15036)
* [cargo: make `"C"` explicit in `extern "C"`](https://github.com/rust-lang/cargo/pull/15034)
* [cargo: setup cargo environment for `cargo rustc --print`](https://github.com/rust-lang/cargo/pull/15026)
* [cargo: simplify SourceID Ord/Eq](https://github.com/rust-lang/cargo/pull/14980)
* [rustdoc-json: include items in stripped modules in `Crate::paths`](https://github.com/rust-lang/rust/pull/135348)
* [rustdoc: use import stability marker in display](https://github.com/rust-lang/rust/pull/135352)
* [rustdoc: use stable paths as preferred canonical paths](https://github.com/rust-lang/rust/pull/135171)
* [rustfmt: drop nightly-gating of the `--style-edition` flag registration](https://github.com/rust-lang/rust/pull/135200)
* [clippy: add new lint `unneeded_struct_pattern`](https://github.com/rust-lang/rust-clippy/pull/13465)
* [clippy: auto-fix `slow_vector_initialization` in some cases](https://github.com/rust-lang/rust-clippy/pull/13947)
* [clippy: do not intersect spans coming from different contexts](https://github.com/rust-lang/rust-clippy/pull/13942)
* [clippy: do not look for significant drop inside `.await` expansion](https://github.com/rust-lang/rust-clippy/pull/13985)
* [clippy: do not propose to elide lifetimes if this causes an ambiguity](https://github.com/rust-lang/rust-clippy/pull/13929)
* [clippy: do not remove identity mapping if mandatory mutability would be lost](https://github.com/rust-lang/rust-clippy/pull/13905)
* [clippy: do not trigger `redundant_pub_crate` in external macros](https://github.com/rust-lang/rust-clippy/pull/13952)
* [clippy: don't emit machine applicable `map_flatten` lint if there are code comments](https://github.com/rust-lang/rust-clippy/pull/13940)
* [clippy: don't suggest to use `cloned` for `Cow` in `unnecessary_to_owned`](https://github.com/rust-lang/rust-clippy/pull/13853)
* [clippy: fix type suggestion for `manual_is_ascii_check`](https://github.com/rust-lang/rust-clippy/pull/13916)
* [clippy: improve `needless_as_bytes` to also detect `str::bytes()`](https://github.com/rust-lang/rust-clippy/pull/13972)
* [clippy: new lint: `manual_ok_err`](https://github.com/rust-lang/rust-clippy/pull/13740)
* [clippy: remove unneeded parentheses in `unnecessary_map_or` lint output](https://github.com/rust-lang/rust-clippy/pull/13932)
* [rust-analyzer: add a new and improved syntax tree view](https://github.com/rust-lang/rust-analyzer/pull/18813)
* [rust-analyzer: add config setting which allows adding additional include paths to the VFS](https://github.com/rust-lang/rust-analyzer/pull/18880)
* [rust-analyzer: re-implement rust string highlighting via tool attribute](https://github.com/rust-lang/rust-analyzer/pull/18906)
* [rust-analyzer: fix JSON project `PackageRoot` buildfile inclusion](https://github.com/rust-lang/rust-analyzer/pull/18866)
* [rust-analyzer: do not compute `prettify_macro_expansion()` unless the "Inline macro" assist has actually been invoked](https://github.com/rust-lang/rust-analyzer/pull/18900)
* [rust-analyzer: do not offer completions within macro strings](https://github.com/rust-lang/rust-analyzer/pull/18832)
* [rust-analyzer: fix `env`/`option_env` macro check disregarding `macro_rules` definitions](https://github.com/rust-lang/rust-analyzer/pull/18884)
* [rust-analyzer: fix `ref` text edit for binding mode hints](https://github.com/rust-lang/rust-analyzer/pull/18920)
* [rust-analyzer: fix a bug with missing binding in MBE](https://github.com/rust-lang/rust-analyzer/pull/18877)
* [rust-analyzer: fix actual token lookup in completion's `expand()`](https://github.com/rust-lang/rust-analyzer/pull/18889)
* [rust-analyzer: fix another issue with fixup reversing](https://github.com/rust-lang/rust-analyzer/pull/18899)
* [rust-analyzer: fix diagnostics not clearing between flychecks](https://github.com/rust-lang/rust-analyzer/pull/18864)
* [rust-analyzer: make edition per-token, not per-file](https://github.com/rust-lang/rust-analyzer/pull/18861)
* [rust-analyzer: implement `#[rust_analyzer::skip]` for bodies](https://github.com/rust-lang/rust-analyzer/pull/18907)
* [rust-analyzer: implement implicit sized bound inlay hints](https://github.com/rust-lang/rust-analyzer/pull/18903)
* [rust-analyzer: improve hover module path rendering](https://github.com/rust-lang/rust-analyzer/pull/18904)

### Rust Compiler Performance Triage

A quiet week with little change to the actual compiler performance. The biggest compiler regression was quickly recognized and reverted. 

Triage done by **@rylev**.
Revision range: [0f1e965f..1ab85fbd](https://perf.rust-lang.org/?start=0f1e965fec3bc2f97b932e9dd8e85fca6d7faadc&end=1ab85fbd7474e8ce84d5283548f21472860de3e2&absolute=false&stat=instructions%3Au)

**Summary**:

| (instructions:u)                   | mean   | range           | count |
|:----------------------------------:|:------:|:---------------:|:-----:|
| Regressions ❌ <br /> (primary)    | 0.4%   | [0.1%, 1.8%]    | 21    |
| Regressions ❌ <br /> (secondary)  | 0.5%   | [0.0%, 2.0%]    | 35    |
| Improvements ✅ <br /> (primary)   | -0.8%  | [-2.7%, -0.3%]  | 6     |
| Improvements ✅ <br /> (secondary) | -10.2% | [-27.8%, -0.1%] | 13    |
| All ❌✅ (primary)                 | 0.2%   | [-2.7%, 1.8%]   | 27    |


4 Regressions, 3 Improvements, 3 Mixed; 3 of them in rollups
44 artifact comparisons made in total

[Full report here](https://github.com/rust-lang/rustc-perf/blob/194b9b1c83f638475d35b5bc27c9617ec3725941/triage/2025-01-14.md)

### [Approved RFCs](https://github.com/rust-lang/rfcs/commits/master)

Changes to Rust follow the Rust [RFC (request for comments) process](https://github.com/rust-lang/rfcs#rust-rfcs). These
are the RFCs that were approved for implementation this week:

* *No RFCs were approved this week.*

### Final Comment Period

Every week, [the team](https://www.rust-lang.org/team.html) announces the 'final comment period' for RFCs and key PRs
which are reaching a decision. Express your opinions now.

#### [RFCs](https://github.com/rust-lang/rfcs/labels/final-comment-period)
* [Supertrait item shadowing v2](https://github.com/rust-lang/rfcs/pull/3624)

#### Tracking Issues & PRs
##### [Rust](https://github.com/rust-lang/rust/issues?q=is%3Aopen+label%3Afinal-comment-period+sort%3Aupdated-desc)
* [remove support for the (unstable) #[start] attribute](https://github.com/rust-lang/rust/pull/134299)
* [fully de-stabilize all custom inner attributes](https://github.com/rust-lang/rust/pull/134276)
* [Uplift `clippy::double_neg` lint as `double_negations`](https://github.com/rust-lang/rust/pull/126604)
* [Optimize `Seek::stream_len` impl for File](https://github.com/rust-lang/rust/pull/125087)
* [[rustdoc] Add sans-serif font setting](https://github.com/rust-lang/rust/pull/133636)
* [Tracking Issue for PathBuf::add_extension and Path::with_added_extension](https://github.com/rust-lang/rust/issues/127292)
* [Make the wasm_c_abi future compat warning a hard error](https://github.com/rust-lang/rust/pull/133951)
* [const-eval: detect more pointers as definitely not-null](https://github.com/rust-lang/rust/pull/133700)
* [Consider fields to be inhabited if they are unstable](https://github.com/rust-lang/rust/pull/133889)
* [disallow repr() on invalid items](https://github.com/rust-lang/rust/pull/133925)

##### [Cargo](https://github.com/rust-lang/cargo/issues?q=is%3Aopen+label%3Afinal-comment-period+sort%3Aupdated-desc)
* *No Cargo Tracking Issues or PRs entered Final Comment Period this week.*

##### [Language Team](https://github.com/rust-lang/lang-team/issues?q=is%3Aopen+label%3Afinal-comment-period+sort%3Aupdated-desc+)
* *No Language Team Proposals entered Final Comment Period this week.*

##### [Language Reference](https://github.com/rust-lang/reference/issues?q=is%3Aopen+label%3Afinal-comment-period+sort%3Aupdated-desc)
* [distinct 'static' items never overlap](https://github.com/rust-lang/reference/pull/1657)

##### [Unsafe Code Guidelines](https://github.com/rust-lang/unsafe-code-guidelines/issues?q=is%3Aopen+label%3Afinal-comment-period+sort%3Aupdated-desc)
* *No Unsafe Code Guideline Tracking Issues or PRs entered Final Comment Period this week.*

#### [New and Updated RFCs](https://github.com/rust-lang/rfcs/pulls)
* [Make trait methods callable in const contexts](https://github.com/rust-lang/rfcs/pull/3762)
* [RFC: Allow packages to specify a set of supported targets](https://github.com/rust-lang/rfcs/pull/3759)

## Upcoming Events

Rusty Events between 2025-01-15 - 2025-02-12 🦀
