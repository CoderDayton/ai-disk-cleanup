# Implementation Plan

## Validation Checklist
- [x] Context Ingestion section complete with all required specs
- [x] Implementation phases logically organized
- [x] Each phase starts with test definition (TDD approach)
- [x] Dependencies between phases identified
- [x] Parallel execution marked where applicable
- [x] Multi-component coordination identified (if applicable)
- [x] Final validation phase included
- [x] No placeholder content remains

## Specification Compliance Guidelines

### How to Ensure Specification Adherence

1. **Before Each Phase**: Complete the Pre-Implementation Specification Gate
2. **During Implementation**: Reference specific SDD sections in each task
3. **After Each Task**: Run Specification Compliance checks
4. **Phase Completion**: Verify all specification requirements are met

### Deviation Protocol

If implementation cannot follow specification exactly:
1. Document the deviation and reason
2. Get approval before proceeding
3. Update SDD if the deviation is an improvement
4. Never deviate without documentation

## Metadata Reference

- `[parallel: true]` - Tasks that can run concurrently
- `[component: component-name]` - For multi-component features
- `[ref: document/section; lines: 1, 2-3]` - Links to specifications, patterns, or interfaces and (if applicable) line(s)
- `[activity: type]` - Activity hint for specialist agent selection

---

## Context Priming

*GATE: You MUST fully read all files mentioned in this section before starting any implementation.*

**Specification**:

- `docs/specs/002-cross-platform-installer/PRD.md` - Product Requirements
- `docs/specs/002-cross-platform-installer/SDD.md` - Solution Design

**Key Design Decisions**:

- **PyInstaller + Native Packers**: Use PyInstaller for core packaging + NSIS (Windows) + AppImage (Linux)
- **Simple Configuration**: Single config file for both platforms
- **Security-First**: Basic code signing (Windows) and checksum verification

**Implementation Context**:

- Commands to run: `python -m installer build windows`, `python -m installer build linux`
- Test commands: `python -m pytest tests/installers/`
- Entry point: Leverage existing `src/ai_disk_cleanup.py`

---

## Implementation Phases

- [ ] **Phase 1: Core Installer Infrastructure**
    - [ ] **Prime Context**: Read SDD Building Block View and existing codebase structure
        - [ ] Read existing `src/platforms/` adapter pattern `[ref: src/platforms/base_adapter.py]`
        - [ ] Examine current `pyproject.toml` dependencies `[ref: pyproject.toml]`
    - [ ] **Write Tests**: Test installer configuration and build orchestration
        - [ ] Test config file loading and validation `[activity: test-writer]`
        - [ ] Test PyInstaller integration and binary creation `[activity: test-writer]`
    - [ ] **Implement**: Basic installer framework
        - [ ] Create `src/installer/` package structure `[activity: implement-code]`
        - [ ] Implement `orchestrator.py` with basic build coordination `[activity: implement-code]`
        - [ ] Create `config.py` for unified configuration management `[activity: implement-code]`
    - [ ] **Validate**: Run tests and check code quality
        - [ ] Run unit tests: `python -m pytest tests/installers/unit/` `[activity: run-tests]`
        - [ ] Code formatting: `ruff format src/installer/` `[activity: format-code]`

- [ ] **Phase 2: Windows Installer Implementation**
    - [ ] **Prime Context**: Read Windows-specific requirements from PRD
        - [ ] Review Windows user personas and security requirements `[ref: PRD.md; lines: 33-45]`
    - [ ] **Write Tests**: Test Windows MSI creation and installation
        - [ ] Test NSIS script generation `[activity: test-writer]`
        - [ ] Test Windows code signing integration `[activity: test-writer]`
    - [ ] **Implement**: Windows builder with NSIS integration
        - [ ] Create `builders/windows_builder.py` with PyInstaller + NSIS workflow `[activity: implement-code]`
        - [ ] Generate NSIS script template for simple installer `[activity: implement-code]`
        - [ ] Implement basic code signing with certificate management `[activity: implement-code]`
    - [ ] **Validate**: Test Windows installer creation
        - [ ] Build Windows installer: `python -m installer build windows` `[activity: run-tests]`
        - ] Verify MSI creation and basic functionality `[activity: run-tests]`

- [ ] **Phase 3: Linux Installer Implementation**
    - [ ] **Prime Context**: Read Linux requirements and AppImage specifications
        - [ ] Review Linux user expectations and package formats `[ref: PRD.md; lines: 177-205]`
    - [ ] **Write Tests**: Test AppImage creation and execution
        - [ ] Test AppImage bundling and dependency management `[activity: test-writer]`
        - [ ] Test Linux executable creation and permissions `[activity: test-writer]`
    - [ ] **Implement**: Linux builder with AppImage support
        - [ ] Create `builders/linux_builder.py` with AppImage workflow `[activity: implement-code]`
        - [ ] Implement AppImage creation with proper dependencies `[activity: implement-code]`
        - [ ] Add GPG signing for Linux packages `[activity: implement-code]`
    - [ ] **Validate**: Test Linux installer creation
        - [ ] Build Linux installer: `python -m installer build linux` `[activity: run-tests]`
        - [ ] Verify AppImage creation and execution `[activity: run-tests]`

- [ ] **Phase 4: Integration & Final Validation**
    - [ ] **Prime Context**: Review all implemented components
        - [ ] Test complete build pipeline: `python -m installer build all` `[activity: run-tests]`
    - [ ] **Integration Tests**: Cross-platform functionality
        - [ ] Test build orchestration with both platforms `[activity: run-tests]`
        - [ ] Verify installer creation and basic functionality `[activity: run-tests]`
        - [ ] Test configuration management across platforms `[activity: run-tests]`
    - [ ] **End-to-End Validation**: Complete user workflows
        - [ ] Install and run Windows MSI on test system `[activity: run-tests]`
        - [ ] Execute Linux AppImage on test system `[activity: run-tests]`
        - [ ] Verify basic application functionality after installation `[activity: run-tests]`
    - [ ] **Final Quality Gates**: Security and performance
        - [ ] Run security scan on generated installers `[activity: run-tests]`
        - [ ] Verify installer sizes are under 100MB `[ref: PRD.md; lines: 191]`
        - [ ] Test installation times are under 3 minutes `[ref: PRD.md; lines: 173]`

## Simple Implementation Timeline

**Week 1: Core Infrastructure**
- Setup installer package structure
- Implement basic configuration and orchestration
- Create PyInstaller integration

**Week 2: Windows Implementation**
- Implement NSIS script generation
- Add Windows code signing
- Create and test Windows MSI installer

**Week 3: Linux Implementation**
- Implement AppImage creation
- Add GPG signing for Linux
- Create and test Linux AppImage installer

**Week 4: Integration & Polish**
- End-to-end testing on both platforms
- Security validation and performance testing
- Documentation and deployment preparation

**Total Time: 4 weeks to production-ready installers**

## Success Criteria

✅ **Windows MSI installer** that installs on Windows 10/11
✅ **Linux AppImage** that runs on major Linux distributions
✅ **Simple build commands**: `python -m installer build windows/linux`
✅ **Code signing** on Windows and checksum verification on Linux
✅ **Installation under 3 minutes** and installer size under 100MB
✅ **95%+ test coverage** of installer components
