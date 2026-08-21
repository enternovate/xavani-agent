class XavaniAgent < Formula
  include Language::Python::Virtualenv

  desc "Self-improving AI agent that creates skills from experience"
  homepage "https://xavani.enternovate.com"
  # Stable source should point at the semver-named sdist asset attached by
  # scripts/release.py, not the CalVer tag tarball.
  url "https://github.com/enternovate/xavani-agent/releases/download/v0.1.2/xavani_agent-0.1.2.tar.gz"
  sha256 "1a5515f08cc77ddb8d4e8ad43b92d1d4ef429ead7a1d00057886f2ed44d05be7"
  license "MIT"

  depends_on "certifi" => :no_linkage
  depends_on "cryptography" => :no_linkage
  depends_on "libyaml"
  depends_on "python@3.14"

  pypi_packages ignore_packages: %w[certifi cryptography pydantic]

  # Refresh resource stanzas after bumping the source url/version:
  #   brew update-python-resources --print-only xavani-agent

  def install
    venv = virtualenv_create(libexec, "python3.14")
    venv.pip_install resources
    venv.pip_install buildpath

    pkgshare.install "skills", "optional-skills"

    %w[xavani xavani-agent xavani-acp].each do |exe|
      next unless (libexec/"bin"/exe).exist?

      (bin/exe).write_env_script(
        libexec/"bin"/exe,
        XAVANI_BUNDLED_SKILLS: pkgshare/"skills",
        XAVANI_OPTIONAL_SKILLS: pkgshare/"optional-skills",
        XAVANI_MANAGED: "homebrew"
      )
    end
  end

  test do
    assert_match "Xavani Agent v#{version}", shell_output("#{bin}/xavani version")

    managed = shell_output("#{bin}/xavani update 2>&1")
    assert_match "managed by Homebrew", managed
    assert_match "brew upgrade xavani-agent", managed
  end
end
