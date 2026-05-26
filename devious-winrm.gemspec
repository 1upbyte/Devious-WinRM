# frozen_string_literal: true

require_relative "lib/devious_winrm/version"

Gem::Specification.new do |spec|
  spec.name = "devious-winrm"
  spec.version = DeviousWinRM::VERSION
  spec.authors = ["Pablo Comino"]
  spec.email = ["pablo@pablocomino.com"]

  spec.summary = "A pentester's PowerShell client."
  spec.description = "A WinRM PowerShell client with zero-config Kerberos helpers."
  spec.homepage = "https://github.com/1upbyte/devious-winrm"
  spec.license = "GPL-3.0-only"
  spec.required_ruby_version = ">= 3.1"

  spec.files = Dir["lib/**/*.rb", "exe/*", "README.md", "LICENSE", "NOTICE"]
  spec.bindir = "exe"
  spec.executables = ["dwrm", "devious-winrm"]
  spec.require_paths = ["lib"]

  spec.add_dependency "gssapi", ">= 1.3", "< 2.0"
  spec.add_dependency "winrm", ">= 2.3", "< 3.0"
end
