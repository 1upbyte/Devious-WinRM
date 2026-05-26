# frozen_string_literal: true

require "open3"
require "tempfile"

module DeviousWinRM
  class KerberosError < StandardError; end

  class Kerberos
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
      @krb5_config_file = nil
    end

    def prepare
      validate!
      configure_krb5
      return if cached_ticket? && @username.nil?

      raise ArgumentError, "No cached Kerberos ticket. Username and password must be provided." if @username.nil? || @password.nil?

      run_kinit
    end

    private

    def validate!
      unless @dc.count(".") >= 2
        raise ArgumentError, "Domain controller must be a fully-qualified domain name (dc.example.com)."
      end

      if Gem.win_platform? && @username
        raise NotImplementedError, "Windows username/password Kerberos is not supported. Use a cached ticket."
      end

      if @nt_hash
        raise NotImplementedError, "Kerberos with NTLM hashes is not supported by the Ruby implementation yet."
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

      message = stderr.empty? ? stdout : stderr
      raise KerberosError, "Kerberos login failed for #{principal}: #{message.strip}"
    rescue Errno::ENOENT
      raise KerberosError, "Running 'kinit' failed. Is Kerberos installed?"
    end

    def kerberos_principal
      user = @username.to_s
      user = user.split("\\", 2).last if user.include?("\\")
      return user if user.include?("@")

      "#{user}@#{@realm}"
    end
  end
end
