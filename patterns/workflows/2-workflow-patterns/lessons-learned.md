# Lessons Learned from Project Implementation

## Best Practices
- **TypeScript + Next.js 14:** Strong typing and modern React patterns improved code quality and reduced runtime errors.
- **Component-Driven Development:** Modular UI (with Shadcn/UI and Tailwind CSS) enabled rapid iteration and consistent design.
- **Automated Testing:** Early adoption of Jest, React Testing Library, and Playwright for E2E tests caught regressions and improved reliability. Test-first approach for new features was highly effective.
- **Security by Design:** Security requirements (CSP, CORS, cookie security, rate limiting, GDPR) were integrated from the start, reducing late-stage rework.
- **Prompt Engineering:** Writing clear, modular prompt files (e.g., `project-status.prompt.md`, `project-docs.prompt.md`) and using prompt boosting techniques led to more accurate, context-aware AI outputs. Iterative prompt refinement improved agent performance.
- **Documentation-Driven Workflow:** Investment in detailed docs (`prd.md`, `frd.md`, `implementation-plan.md`, `ui-guidelines.md`, `architecture-specifications.md`, `case-studies.md`) provided a single source of truth, improved onboarding, and enabled both the AI agent and human collaborators to track status, requirements, and decisions efficiently.
- **Agent Collaboration via agent-work.md:** Maintaining an `agent-work.md` file enabled seamless, asynchronous collaboration with the AI agent—tracking current tasks, subtasks, issues, and future work. This file, along with issues and clarification logs, solved for memory/context loss when hitting token limits in LLMs (GPT, Claude, Gemini).
- **CI/CD & Linting:** Automated checks and code formatting (Prettier, ESLint) maintained codebase health.
- **Tooling:** pnpm for fast, reliable package management; AWS Amplify for seamless deployment; Upstash for scalable rate limiting; Substack RSS for content syndication.

## Pitfalls to Avoid
- **Test Coverage Gaps:** Some features (rate limiting, newsletter) initially lacked full test coverage, leading to late bug discovery. Solution: enforce minimum coverage thresholds.
- **API Mocking Issues:** Early API route tests failed due to incomplete mocks. Resolution: improved test helpers and closer alignment with handler logic.
- **Assumptions About Integrations:** HubSpot and Substack integrations required more custom logic than anticipated. Mitigation: prototype integrations early and document API limitations.
- **Manual Content Migration:** Delays and confusion arose from unclear ownership of PDF uploads and content migration. Solution: assign clear responsibilities and checklist for assets.
- **Dependency Warnings:** Outdated testing libraries caused warnings. Regular dependency audits are needed.
- **Documentation Drift:** Without regular updates, documentation can become outdated. Solution: schedule doc reviews at each project milestone.
- **Context Loss in LLMs:** Hitting token/context limits in AI agents can cause loss of project memory. Solution: maintain up-to-date, modular documentation and use files like `agent-work.md` for persistent context.

## May 2025 Updates

- **Image Warnings:**
  - All usages of Next.js `Image` and custom `OptimizedImage` with the `fill` prop were reviewed.
  - Confirmed all parents have valid positioning (`relative`, `absolute`, etc.) as required by Next.js.
  - Image warnings in the backlog were false positives, not caused by incorrect code. Documented findings in `agent-work.md`.

- **Hydration Mismatch Error:**
  - Investigated persistent hydration mismatch warning in the browser console.
  - Determined the mismatch was caused by browser extensions (e.g., Grammarly) injecting attributes into the DOM before React hydrates.
  - This is not a bug in the codebase; it is a false positive that only appears for users with certain extensions installed. No code changes required.

- **Theme Switching Animation:**
  - Refactored CSS and logic for theme switching to ensure smooth color transitions.
  - Removed unnecessary body fade/blur and improved best-practice color transitions.

- **Testing Improvements:**
  - Updated all `act` imports to use `react` to resolve deprecation warnings.
  - Fixed type errors in test mocks and added missing `data-testid` attributes for theme options.
  - Resolved failing tests for theme switching and newsletter subscription.

- **Resource Preload Warning:**
  - Removed `/hero.avif` preload from layout to resolve resource preload warning.

- **Security and Compliance:**
  - Completed cookie security, CSP, CORS, and sensitive data exposure prevention tasks.
  - Implemented and tested user data access/deletion mechanisms and privacy policy updates.

- **Rate Limiter Test Coverage:**
  - Achieved 100% test coverage for the rate limiter logic (`lib/rate-limit.ts`).
  - Added a direct unit test for `logRateLimitInfo` to ensure all functions are covered.
  - Patched test setup to handle `process.env.NODE_ENV` and custom Jest mocks for Upstash/Redis.
  - All error paths, edge cases (including Redis failures and custom identifier usage), and logging are now fully tested.
  - All tests pass, ensuring robust and reliable rate limiting for API routes.

- **General:**
  - Documented all findings, fixes, and next steps in `agent-work.md` for future reference.

---

## Theme Switching Animation: Lessons Learned (May 2025)

- **Issue:** Theme switching animation (fade/blur or color transition) was not visible despite correct CSS and event logic.
- **Root Cause:** The `disableTransitionOnChange` prop was set on the `ThemeProvider`, which disables all CSS transitions during theme changes. This is a feature of `next-themes` to prevent unwanted transitions, but it also blocks intended smooth color transitions.
- **Resolution:** I asked the agent to review the ui-guidelines.md for to review the recommended approach for theme transitions. The guidelines provided the exact implementation details for global.css and layout.ts. Remove the `disableTransitionOnChange` prop from the `ThemeProvider` in `layout.tsx`. This allows the global CSS transitions (e.g., `transition-colors duration-300`) to work as intended, resulting in a smooth, accessible theme switch.
- **Best Practice:** Always check for framework or library props that may override or disable CSS transitions. For `next-themes`, only use `disableTransitionOnChange` if you want to prevent all transitions. For most modern UI/UX, smooth color transitions are preferred and should be enabled.
- **Reference:** See UI guidelines section 3.6 and 3.5 for animation and theme switching best practices.

---

## [May 16, 2025] Download Case Study API Jest Test Removal
- The file `__tests__/api/download-case-study.test.ts` was removed due to persistent ESM/CJS interop issues with Next.js API route handler imports in Jest.
- All endpoint security tests for this API are now covered by Playwright integration tests (`e2e/download-case-study-api.spec.ts`).
- See `agent-work.md` for tracking and post-launch plans to revisit direct API handler unit tests if/when ecosystem support improves.

---

## [May 16, 2025] Sensitive Data Exposure Jest Test Removal
- The file `__tests__/security/sensitive-data-exposure.test.ts` was removed due to persistent ESM/CJS interop issues with Next.js API route handler imports in Jest.
- Endpoint security for Case Study Download API is now covered by Playwright integration tests (`e2e/download-case-study-api.spec.ts`).
- Newsletter API security tests remain covered by Jest.
- See `agent-work.md` for tracking and post-launch plans to revisit direct API handler unit tests if/when ecosystem support improves.

---

## [May 22, 2025] Resolving "self is not defined" Error in Next.js Server Builds

### Issue
- **Error Message:** `unhandledRejection ReferenceError: self is not defined at Object.<anonymous> (.next/server/npm..pnpm.js:1:1)`
- **Root Cause:** Some packages in `node_modules` reference the browser-specific global `self` variable, which doesn't exist in Node.js server environments.
- **Context:** This error occurs during Next.js build process when bundling server-side code that references browser globals.

### Solutions Attempted
1. **Server-side polyfill file:** Created `/polyfills/self.js` to define `self = global` in Node.js environments
2. **Custom webpack plugin:** Implemented a plugin to inject polyfill at build time
3. **API route imports:** Added polyfill imports to individual API routes
4. **next.config.mjs modifications:** Added polyfill directly in the Next.js config file
5. **DefinePlugin approach:** Used webpack's DefinePlugin to replace `self` with `global`
6. **NODE_OPTIONS approach:** Modified package.json scripts to use the `--require` flag

### Initial Solution (Which Caused 400 Errors)
The initial solution combined several approaches:

1. **Enhanced server-polyfills.js:**
   - Created a comprehensive polyfill that handles not just `self` but also other browser globals (`window`, `document`, `SVGElement`, `HTMLElement`)
   - Implemented proper DOM-like interfaces with methods like `addEventListener` and `querySelector`

2. **Module aliasing for problematic modules:**
   - Created mock implementations for libraries causing issues (ioredis, upstash/redis)
   - Used a custom ES module loader to intercept and replace problematic imports

3. **Custom build script (build-with-mocks.js):**
   - Created a dedicated build wrapper script that configures a safe build environment
   - Sets proper environment variables to prevent actual API calls during build
   - Uses Node's experimental module loader to replace problematic modules

4. **Rate limiting code improvements:**
   - Added resilience to Redis client code to handle build-time scenarios
   - Implemented proper conditional checks before using external services

### Fixing the 400 Error Issue (May 22, 2025 Update)
While the comprehensive polyfill solution fixed the "self is not defined" error, it introduced a new issue: 400 errors appeared on every page of the site. This was caused by the polyfills interfering with Next.js middleware execution.

#### Root Cause Analysis:
- The comprehensive browser polyfills (window, document, HTMLElement, SVGElement, etc.) were being applied in all environments, including Edge runtime used by Next.js middleware.
- Next.js middleware runs in a different JavaScript environment than the server, and injecting these polyfills interfered with its normal operation.

#### Final Solution:
1. **Simplified server-polyfills.js:**
   - Reduced the polyfill to only provide the essential `self` global variable
   - Added runtime environment detection to only apply in Node.js environments, not in Edge runtime
   - Removed all excessive browser polyfills that were interfering with middleware
   
2. **Runtime Environment Detection:**
   ```javascript
   const isNodeRuntime = typeof process !== 'undefined' && 
                        (!process.env.NEXT_RUNTIME || process.env.NEXT_RUNTIME === 'nodejs');
   
   if (isNodeRuntime) {
     if (typeof self === 'undefined' && typeof global !== 'undefined') {
       globalThis.self = globalThis;
       global.self = global;
     }
   }
   ```

3. **Verification:**
   - Successfully built the application with `pnpm build` without any "self is not defined" errors
   - Ran both development and production servers with proper 200 status codes on all pages
   - Confirmed API endpoints are working correctly without middleware interference

### Key Takeaways
- **Hidden Browser Dependencies:** Many NPM packages implicitly depend on browser globals even when used server-side.
- **Early Detection:** Implement comprehensive server-side polyfills early in projects to prevent build failures late in development.
- **Module Mocking Strategy:** For problematic modules/services, implement a mock-first strategy during builds.
- **Environment-Based Code Paths:** Design service clients (Redis, APIs, etc.) with environment-aware code paths that can safely run during builds.
- **Multiple Defense Layers:** Combining polyfills, webpack customization, and module aliasing provides the most robust solution.
- **Minimal Polyfills:** When adding polyfills, follow the principle of least intervention. Add only what's strictly necessary to fix specific issues.
- **Runtime Environment Detection:** Always check which JavaScript runtime environment code is running in before applying polyfills.
- **Next.js Middleware Considerations:** Middleware runs in Edge runtime, which has different requirements from Node.js server code.

### Implementation Details
- See `server-polyfills.js` for the minimal polyfill implementation that avoids middleware issues
- The `build-with-mocks.js` and `module-alias-loader.mjs` provide additional layers of protection for the build process
- Added a `build:safe` script to package.json for production builds
- Verified solution works in both development and production environments

### Testing Strategy
- Use HTTP status checking (e.g., `curl -I http://localhost:3000`) to verify middleware is functioning correctly
- Test all major sections of the site after polyfill changes
- Verify both development and production builds to ensure consistency across environments

---

## [May 25, 2025] Next.js to React (Vite) Migration & AWS Amplify Deployment

### Migration Success Factors
- **Clean Architecture:** Original Next.js codebase's modular design made migration easier. Components were well-isolated with clear responsibilities.
- **Static-First Approach:** Site was already designed for static generation, making the move to a Vite-based SPA straightforward.
- **TypeScript Benefits:** Strong typing caught integration issues early during the migration process.
- **Tailwind CSS Portability:** UI styling remained consistent as Tailwind classes worked seamlessly across frameworks.

### Key Migration Steps
1. **Initial Setup**
   - Created new Vite + React + TypeScript project
   - Migrated npm dependencies, ensuring version compatibility
   - Ported Tailwind CSS configuration and theme settings

2. **Component Migration**
   - Moved components from pages to React Router routes
   - Updated imports to use new project structure
   - Converted any Next.js-specific features (Image, Link) to standard React equivalents

3. **Routing Updates**
   - Replaced Next.js file-based routing with React Router
   - Implemented client-side routing patterns
   - Added proper fallback for 404 handling via redirects.json

4. **Asset Management**
   - Reorganized static assets under `public/` directory
   - Updated image references to use proper public paths
   - Implemented proper lazy loading for images

### AWS Amplify Deployment Lessons
1. **Configuration Best Practices**
   - Created minimal `amplify.yml` focusing on build essentials
   - Used `--legacy-peer-deps` to resolve React 19 dependency conflicts
   - Properly configured build output directory (`dist`)

2. **Environment Variables**
   - Maintained clear separation between development and production variables
   - Used Amplify's environment variable system effectively
   - Protected sensitive data (API keys, credentials) appropriately

3. **Build Performance**
   - Implemented efficient node_modules caching
   - Optimized build commands for faster deployment
   - Used proper dependency installation flags

4. **Common Issues Solved**
   - Resolved ERESOLVE npm errors using `--legacy-peer-deps`
   - Fixed TypeScript configuration for proper React types
   - Addressed mobile menu visibility issues through iterative UI improvements

### Key Learnings
1. **Framework Migration**
   - Start with routing: it's the foundation of the application structure
   - Test component rendering early and often during migration
   - Keep environmental configurations (development/production) separate
   - Document breaking changes and required updates

2. **Amplify Deployment**
   - Begin with a minimal working configuration
   - Test builds locally before pushing to Amplify
   - Use Amplify's preview environments for testing
   - Implement proper error handling for build failures

3. **UI/UX Considerations**
   - Maintain consistent theming across the migration
   - Test responsive design thoroughly
   - Verify accessibility features remain intact
   - Address mobile-specific issues promptly

### Best Practices Established
1. **Development Workflow**
   - Use TypeScript consistently for type safety
   - Maintain clear component boundaries
   - Keep build configurations simple and documented
   - Regular testing across devices and browsers

2. **Deployment Process**
   - Verify environment variables before each deployment
   - Test builds locally using `npm run build`
   - Monitor build logs for potential issues
   - Maintain backup deployment options

3. **Documentation**
   - Keep track of breaking changes
   - Document configuration updates
   - Maintain clear deployment instructions
   - Record solutions to common issues

### Future Recommendations
1. **Project Structure**
   - Consider micro-frontend architecture for larger applications
   - Implement proper code splitting from the start
   - Use proper asset optimization techniques
   - Plan for scalability in routing and state management

2. **Build/Deploy Pipeline**
   - Implement automated testing in CI/CD
   - Use proper caching strategies
   - Monitor build performance
   - Regular dependency updates

3. **Maintenance**
   - Regular security audits
   - Performance monitoring
   - Dependency updates
   - Documentation reviews

This migration and deployment experience has demonstrated the importance of:
- Clean, modular architecture
- Strong typing with TypeScript
- Proper build configuration
- Thorough testing across environments
- Clear documentation of processes and solutions

These lessons will inform future projects and migrations, particularly in maintaining clean architecture and ensuring smooth deployment processes.

---

# Lessons Learned: API Security Endpoint Testing with Next.js, Jest, and Playwright

## Challenges with Jest and Next.js API Route Testing
- **ESM/CJS Interop Issues:** Next.js API route handlers and Jest have persistent compatibility issues due to differences in ESM/CJS module resolution, especially when using path aliases (e.g., `@/lib/...`).
- **Direct Handler Import Fails:** Importing or requiring API route handlers directly in Jest tests (from `lib/handlers/...`) consistently results in `undefined` or `not a function` errors, regardless of export style.
- **Route File Import Fails:** Even requiring the route file's exported handler (e.g., `require('../../app/api/download-case-study/route').POST`) fails due to how Next.js and Jest resolve modules.
- **Dynamic Imports Don't Help:** Using dynamic imports (with either path aliases or relative paths) in the route file does not resolve the issue and can break Next.js runtime behavior.
- **Playwright Integration Works:** The only reliable way to test API endpoints in this stack is via Playwright (or similar integration/E2E tools) that hit the running server, bypassing all module resolution issues.

## Solution
- **Removed failing Jest API endpoint tests.**
- **Migrated security tests to Playwright integration tests.**
- **Documented the need to revisit Jest/Next.js API route testing post-launch, possibly with a pure ESM setup or improved tooling.**

## Key Takeaways
- **Success Factors:** Early investment in testing, security, documentation, and prompt engineering paid off at launch. Modular architecture and clear UI guidelines enabled fast, high-quality delivery.
- **Innovations:** Gated PDF downloads with HubSpot integration, robust cookie/data privacy controls, Substack RSS as a no-CMS content solution, and prompt-driven agent workflows.
- **Team Strengths:** Proactive risk management, rapid bug resolution, and strong communication (clarification.md, issues.md, agent-work.md) were critical.
- **Optimization Opportunities:** Further automate content migration, increase test coverage for rate limiting and edge cases, and continue refining prompt and documentation practices.

## Recommendations
- **Enforce Test Coverage:** Set and monitor minimum thresholds for all new features.
- **Prototype Integrations:** Build and test third-party integrations early in the project.
- **Automate Asset Management:** Use scripts or CI/CD for content and asset migration to reduce manual errors.
- **Regular Dependency Audits:** Schedule monthly reviews of dependencies and address warnings promptly.
- **Continue Documentation Culture:** Maintain detailed, living documentation for all phases and handoffs. Schedule regular reviews to prevent drift.
- **Resource Planning:** Assign clear ownership for content, security, and deployment tasks in future projects.
- **Prompt Engineering:** Develop and maintain modular prompt files for all major project tasks. Use prompt boosting and iterative refinement to improve AI agent output.
- **Agent Collaboration:** Always use a persistent `agent-work.md` (or equivalent) file to track current and future tasks, issues, and notes for AI/human collaboration. This is essential for overcoming LLM context/token limits.
- **Optimal AI+Project Setup:**
  - Use a documentation-driven approach: maintain up-to-date `prd.md`, `frd.md`, `implementation-plan.md`, `ui-guidelines.md`, and `agent-work.md`.
  - Store all prompts and instructions in version-controlled files.
  - Use modular, well-structured documentation to enable both AI and human contributors to quickly regain context and contribute effectively.
  - Review and update documentation and prompt files at every major milestone.

## Ongoing Best Practices
- Always verify browser-only code is used in client components or guarded with `typeof window !== "undefined"`.
- Document the cause of any persistent warnings or errors, especially if they are environment-specific (e.g., browser extensions).
- Keep automated tests up to date with code changes and document any fixes for future maintainers.
