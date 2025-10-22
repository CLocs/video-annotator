# Windows Code Signing Guide for VideoMarker

Code signing helps users trust your executable by verifying it comes from you and hasn't been tampered with.

## Overview

There are two main approaches:

1. **Self-Signed Certificate** (Free, but shows security warnings)
2. **Commercial Certificate** (Paid, eliminates most warnings)

---

## Option 1: Self-Signed Certificate (For Testing)

### Prerequisites
- Windows SDK (includes `signtool.exe` and `makecert.exe`)
- Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

### Steps

#### 1. Create Certificate (One-time setup)
```cmd
# Run as Administrator
.\codesign_windows.bat create-cert
```

Or manually:
```cmd
makecert -r -pe -n "CN=Your Name" -ss My -sr CurrentUser ^
  -sky signature -eku 1.3.6.1.5.5.7.3.3 VideoMarker.cer
```

#### 2. Install Certificate
1. Double-click `VideoMarker.cer`
2. Click "Install Certificate"
3. Select "Current User"
4. Choose "Place all certificates in the following store"
5. Browse and select "Trusted Root Certification Authorities"
6. Complete the wizard

#### 3. Sign Your Executable
```cmd
.\codesign_windows.bat sign
```

Or manually:
```cmd
signtool sign /n "Your Name" /t http://timestamp.digicert.com ^
  /fd SHA256 /v dist\VideoMarker.exe
```

#### 4. Verify Signature
```cmd
signtool verify /pa /v dist\VideoMarker.exe
```

### Limitations
- Still shows "Unknown Publisher" warnings
- Windows SmartScreen may still block it initially
- Not suitable for public distribution

---

## Option 2: Commercial Code Signing Certificate (Recommended for Distribution)

### Step 1: Purchase a Certificate

**Recommended Certificate Authorities:**
- **DigiCert** - https://www.digicert.com/signing/code-signing-certificates
  - EV Code Signing: ~$400-500/year (best, instant SmartScreen reputation)
  - Standard Code Signing: ~$200-300/year

- **Sectigo (Comodo)** - https://sectigo.com/ssl-certificates-tls/code-signing
  - More affordable: ~$150-200/year
  - Resellers often cheaper: ~$80-100/year

- **SSL.com** - https://www.ssl.com/certificates/code-signing/
  - Competitive pricing

- **GlobalSign** - https://www.globalsign.com/en/code-signing-certificate

### Certificate Types

**Standard Code Signing**
- ✅ Eliminates "Unknown Publisher" warning
- ✅ Shows your company/name as publisher
- ❌ Still may trigger SmartScreen until you build reputation
- 💰 ~$150-300/year

**EV (Extended Validation) Code Signing** 
- ✅ Everything from Standard
- ✅ **Immediate SmartScreen reputation** (no warnings)
- ✅ Stored on hardware token (more secure)
- ✅ Best for public distribution
- 💰 ~$400-500/year

### Step 2: Complete Validation

The CA will verify your identity:
- Business documents (for companies)
- Government ID (for individuals)
- Phone verification
- Address verification

⏱️ Takes 1-7 days depending on certificate type

### Step 3: Receive Your Certificate

**For Standard Certificates:**
- Receive `.pfx` or `.p12` file
- Store it securely with a strong password

**For EV Certificates:**
- Receive USB hardware token (YubiKey, SafeNet eToken, etc.)
- Token contains certificate and requires PIN

### Step 4: Sign Your Executable

#### Using PowerShell (with PFX file):
```powershell
# Set your certificate path and password
$certPath = "C:\path\to\your\certificate.pfx"
$certPassword = ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText
$cert = Get-PfxCertificate -FilePath $certPath -Password $certPassword

# Sign the executable
Set-AuthenticodeSignature -FilePath "dist\VideoMarker.exe" -Certificate $cert `
  -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
```

#### Using SignTool (Command Line):
```cmd
# For PFX file
signtool sign /f "certificate.pfx" /p "YourPassword" ^
  /t http://timestamp.digicert.com /fd SHA256 ^
  /d "VideoMarker" /du "https://github.com/yourusername/video-annotator" ^
  dist\VideoMarker.exe

# For certificate in Windows Certificate Store
signtool sign /n "Your Company Name" ^
  /t http://timestamp.digicert.com /fd SHA256 ^
  /d "VideoMarker" /du "https://github.com/yourusername/video-annotator" ^
  dist\VideoMarker.exe

# For hardware token (EV certificate)
signtool sign /sha1 "THUMBPRINT" ^
  /t http://timestamp.digicert.com /fd SHA256 ^
  /d "VideoMarker" /du "https://github.com/yourusername/video-annotator" ^
  dist\VideoMarker.exe
```

### Step 5: Verify the Signature

```cmd
# Verify signature
signtool verify /pa /v dist\VideoMarker.exe

# View signature details
Get-AuthenticodeSignature dist\VideoMarker.exe | Format-List
```

---

## Important Notes

### Timestamps
**Always include a timestamp server** when signing:
- DigiCert: `http://timestamp.digicert.com`
- Sectigo: `http://timestamp.sectigo.com`
- GlobalSign: `http://timestamp.globalsign.com`

Timestamps ensure your signature remains valid even after your certificate expires.

### Windows SmartScreen
- **EV Certificates**: Instant reputation, no warnings
- **Standard Certificates**: Need to build reputation over time
  - Initially may show warnings
  - Reputation improves as more users download and run your app
  - Microsoft tracks downloads and user behavior

### Security Best Practices
1. **Never commit certificates to git**
2. **Use strong passwords for PFX files**
3. **Store certificates securely** (password manager, encrypted drive)
4. **For teams**: Use Azure Key Vault or similar for certificate storage
5. **Hardware tokens**: Store in safe place, never share PIN

---

## Automated Signing in CI/CD

### GitHub Actions Example:
```yaml
name: Build and Sign

on: [push, release]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build executable
        run: .\build.bat
      
      - name: Import certificate
        run: |
          $pfxBytes = [System.Convert]::FromBase64String("${{ secrets.CERT_BASE64 }}")
          [IO.File]::WriteAllBytes("cert.pfx", $pfxBytes)
      
      - name: Sign executable
        run: |
          signtool sign /f cert.pfx /p "${{ secrets.CERT_PASSWORD }}" `
            /t http://timestamp.digicert.com /fd SHA256 `
            dist\VideoMarker.exe
      
      - name: Clean up certificate
        run: Remove-Item cert.pfx
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: VideoMarker-Signed
          path: dist\VideoMarker.exe
```

### Azure Key Vault (For Enterprise):
```powershell
# Sign using certificate from Azure Key Vault
.\AzureSignTool.exe sign `
  --azure-key-vault-url "https://yourvault.vault.azure.net" `
  --azure-key-vault-certificate "YourCertName" `
  --azure-key-vault-client-id "your-client-id" `
  --azure-key-vault-tenant-id "your-tenant-id" `
  --azure-key-vault-client-secret "your-secret" `
  --timestamp-rfc3161 "http://timestamp.digicert.com" `
  dist\VideoMarker.exe
```

---

## Cost Comparison

| Provider | Standard | EV | Notes |
|----------|----------|----|----|
| DigiCert | $239/yr | $474/yr | Premium, best support |
| Sectigo Direct | $179/yr | $459/yr | Good value |
| Sectigo Resellers | $80-120/yr | $300-400/yr | Best price |
| SSL.com | $199/yr | $399/yr | Competitive |
| Certum | €90/yr | €300/yr | European CA |

*Prices as of 2024, subject to change*

---

## Quick Start Checklist

- [ ] Install Windows SDK (for signtool)
- [ ] Build your executable
- [ ] For testing: Create self-signed certificate
- [ ] For production: Purchase commercial certificate
- [ ] Complete identity validation (2-7 days)
- [ ] Receive and install certificate
- [ ] Sign your executable with timestamp
- [ ] Verify signature
- [ ] Test on clean Windows machine
- [ ] Distribute to users

---

## Resources

- **Windows SDK**: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
- **SignTool Documentation**: https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- **Code Signing Best Practices**: https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/code-signing-best-practices
- **SmartScreen Information**: https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-defender-smartscreen/

---

## Troubleshooting

### "SignTool Error: No certificates were found that met all the given criteria"
- Certificate not installed in Windows Certificate Store
- Wrong certificate name in `/n` parameter
- Certificate expired

### "The file is signed but the signature verification failed"
- Timestamp server unreachable (try different timestamp server)
- Certificate has been revoked
- System time/date incorrect

### Windows SmartScreen still shows warnings (with valid certificate)
- Normal for Standard certificates initially
- Build reputation by having more users download and run
- Consider upgrading to EV certificate for instant reputation
- Submit to Microsoft for review: https://www.microsoft.com/wdsi/filesubmission

---

## Need Help?

If you encounter issues:
1. Check certificate is installed: `certmgr.msc`
2. Verify signtool is in PATH
3. Test with self-signed cert first
4. Contact your CA's support for certificate issues
