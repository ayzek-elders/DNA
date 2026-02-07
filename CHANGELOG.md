# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial package structure with automated GitHub Actions publishing
- Comprehensive documentation for release process

## [0.1.0] - 2025-02-07

### Added
- Event-driven graph engine core functionality
- ObserverGraph for orchestrating nodes and edges
- GraphEvent system with multiple event types
- Base interfaces (IProcessor, IMiddleware, IObserver, ISubject, ILifecycle)
- BaseNode abstract class for creating custom nodes
- HTTP nodes (GET, POST, PUT, DELETE, PATCH) with retry logic
- MQTT nodes for pub/sub messaging (MQTTSubscriberNode, MQTTPublisherNode)
- MapperNode for JSON data transformation using JMESPath
- SwitchNode for conditional routing using JSON Logic
- MailSenderNode for SMTP email notifications
- GroqNode for LLM integration (requires langchain-groq)
- Comprehensive README with usage examples
- Package building and publishing infrastructure
- GitHub Actions for CI/CD

### Documentation
- README.md with installation and quick start guide
- RELEASE.md with detailed release process
- Node-specific documentation (MQTT, Mapper, Switch)
- Engine architecture documentation

### Infrastructure
- Python 3.13+ support
- UV package manager integration
- Proprietary license
- GitHub Packages publishing
- Automated version bumping script