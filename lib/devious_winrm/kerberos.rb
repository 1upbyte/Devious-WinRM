# frozen_string_literal: true

require "open3"
require "tempfile"
require "tmpdir"

module DeviousWinRM
  class KerberosError < StandardError; end

  class Kerberos
    LM_HASH = "aad3b435b51404eeaad3b435b51404ee"

    attr_reader :dc, :realm, :ccache_path, :krb5_config_path

    def initialize(dc:, username: nil, password: nil, nt_hash: nil)
      @dc = dc.upcase
      @username = username
      @password = password
      @nt_hash = nt_hash
      @realm = realm_from_dc(@dc)
      @ccache_path = nil
      @krb5_config_path = nil
      @ccache_file = nil
      @ccache_dir = nil
      @krb5_config_file = nil
    end

    def prepare
      validate!
      configure_krb5
      return if cached_ticket? && @username.nil?

      if @username.nil? || (@password.nil? && @nt_hash.nil?)
        raise ArgumentError, "No cached Kerberos ticket. Username and password/hash must be provided."
      end

      @nt_hash ? run_get_tgt : run_kinit
    end

    private

    def validate!
      unless @dc.count(".") >= 2
        raise ArgumentError, "Domain controller must be a fully-qualified domain name (dc.example.com)."
      end

      if Gem.win_platform? && @username
        raise NotImplementedError, "Windows username/password Kerberos is not supported. Use a cached ticket."
      end

      return unless @nt_hash

      unless @nt_hash.match?(/\A[0-9a-fA-F]{32}\z/)
        raise ArgumentError, "NTLM hash must be 32 hexadecimal characters."
      end
    end

    def realm_from_dc(dc)
      parts = dc.split(".")
      parts.last(2).join(".")
    end

    def configure_krb5
      data = <<~KRB5
        [libdefaults]
            default_realm = #{@realm}
            dns_lookup_realm = false
            dns_lookup_kdc = false
            rdns = false
            udp_preference_limit = 1

        [realms]
            #{@realm} = {
                kdc = #{@dc}
                admin_server = #{@dc}
            }

        [domain_realm]
            .#{@realm.downcase} = #{@realm}
            #{@realm.downcase} = #{@realm}
      KRB5

      @krb5_config_file = Tempfile.new(["devious-winrm", ".krb5.conf"])
      @krb5_config_file.write(data)
      @krb5_config_file.flush
      @krb5_config_path = @krb5_config_file.path
      ENV["KRB5_CONFIG"] = @krb5_config_path
    end

    def cached_ticket?
      system("klist", "-s", out: File::NULL, err: File::NULL)
    rescue Errno::ENOENT
      raise KerberosError, "Running 'klist' failed. Is Kerberos installed?"
    end

    def run_kinit
      @ccache_file = Tempfile.new(["devious-winrm", ".ccache"])
      @ccache_path = @ccache_file.path
      ENV["KRB5CCNAME"] = "FILE:#{@ccache_path}"

      principal = kerberos_principal
      stdout, stderr, status = Open3.capture3("kinit", principal, stdin_data: "#{@password}\n")
      return if status.success?

      message = short_error(stderr.empty? ? stdout : stderr)
      raise KerberosError, "Kerberos login failed for #{principal}: #{message.strip}"
    rescue Errno::ENOENT
      raise KerberosError, "Running 'kinit' failed. Is Kerberos installed?"
    end

    def run_get_tgt
      @ccache_dir = Dir.mktmpdir("devious-winrm")

      stdout, stderr, status = Open3.capture3(
        "getTGT.py",
        "-hashes", "#{LM_HASH}:#{@nt_hash}",
        "-dc-ip", @dc.downcase,
        "#{@realm}/#{kerberos_username}",
        chdir: @ccache_dir
      )
      unless status.success?
        message = short_error(stderr.empty? ? stdout : stderr)
        raise KerberosError, "Kerberos hash login failed for #{kerberos_username}@#{@realm}: #{message.strip}"
      end

      @ccache_path = Dir.glob(File.join(@ccache_dir, "*.ccache")).first
      unless @ccache_path
        message = short_error(stderr.empty? ? stdout : stderr)
        raise KerberosError, "Kerberos hash login failed for #{kerberos_username}@#{@realm}: #{message}"
      end

      ENV["KRB5CCNAME"] = "FILE:#{@ccache_path}"
    rescue Errno::ENOENT
      raise KerberosError, "Running 'getTGT.py' failed. Is impacket installed?"
    end

    def kerberos_principal
      user = kerberos_username
      return user if user.include?("@")

      "#{user}@#{@realm}"
    end

    def kerberos_username
      user = @username.to_s
      user = user.split("\\", 2).last if user.include?("\\")
      user = user.split("/", 2).last if user.include?("/")
      user = user.split("@", 2).first if user.include?("@")
      user
    end

    def short_error(message)
      lines = message.to_s.lines.map(&:strip).reject(&:empty?)
      lines.reverse.find { |line| !line.start_with?("Impacket v") } || "unknown error"
    end
  end
end
