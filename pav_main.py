
<!DOCTYPE html>
<html
  lang="en"
  
  data-color-mode="auto" data-light-theme="light" data-dark-theme="dark"
  data-a11y-animated-images="system" data-a11y-link-underlines="true"
  >


  <head>
    <meta charset="utf-8">

  <title>Initiating SAML single sign-on</title>
  <meta http-equiv="refresh" content="0;url=https://login.microsoftonline.com/6e06e42d-6925-47c6-b9e7-9581c7ca302a/saml2?RelayState=ViLHS0p0OiJG5l900tbeK4tycY_Lj_BICog5X6Wuxz2CxJXwWIl5WPpssrIvJdWRq4SKhjDUnl1jQ6lie8EgTDAUnmpuW4eJ3_3NwDET8hg&amp;SAMLRequest=jZLNbtswEITveQqBd0kU9WOLsBwoMYoaSGMhdnvIpaColU2AIl2Scts8fWnFQYMWCXJdzizn293F9a9BBicwVmhVoSTC6Hp5tbBskEdaj%2B6gHuDHCNYFXqcsnR4qNBpFNbPCUsUGsNRxuq2%2F3FESYXo02mmuJXpled%2FBrAXjfAAUrFcV%2Bo4Jm7dFmvcdn5VslneQcZaVPMN9j%2BdpQnCR4rwrABdthktS5pD3PZuTpMsInhPfxtoR1so6plyFCCZ5mJCQpDucU1zQhDyi4NsLtI%2BAgpVnFIq5qXJw7mhpHEu9FyoaBDfa6t5pJYWCiOshPv8NGenCovS9sxkvwraEWVjm84TPOEs9Q3wmn8I0nlCcoEI9kxZQ0FxGdCNUJ9T%2B%2Fem0zyJLP%2B92TdhstjsU1C8Tu9XKjgOYLZiT4PD14e5v%2Br1wh7GNOjiB1EcwEZNSMPUUCT1Fi%2FmzGS2nfdNpaGb5Afsifm24XMu9T75eNVoK%2FjuopdQ%2Fbw0w56mdGT30J20G5t5mTaJkqogu7CcpHZU9Ahe9gA7Fl5AeuBNnchvca3cDXgpvbdgLNmpj6t6B%2BVeTJJPGt43%2FP%2Fbl1R8%3D&amp;SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&amp;Signature=EHlRmWGXO32GF4cmrBYhTDQvTCeZEfos5xXzHZC4d1xt2EELUWiqt4vgGbrEhIp%2B8%2BAsWqRDowMgo1fiuHMRabweemK5trOE7nnYBYAlqyRihrMbDfFKnPzi1unDUvrRJbBS2s8R9maM%2FfIatsFcAitlVsm3HfPYiD%2BOVHX%2Ftbcw1BlzverQOLfP%2FOS40Ytb6rM6YqAq2bM5aGRN5UU0MrF%2F8gstWw8B%2BNfmuiQzxIkstDCnAKhA0RO2FTQgs6m3dkeoDZyKX3bNpAKrh%2Bc6TQ2FK%2FZWf1ftXtTmeW0o66cX6zYtnHg5NNck618sZoXYRsN3WmwuiuYGN4nllRZ9%2BZMXGy3DnvHwXX46ojAODprW1mIeJFt8BJ18MCduvUsU9BPwof7%2BLlR%2Bi5oKsXfXzdEkrMDwy4NdrbJnvV22SjCJtVxfSWyZ6thtwXWd%2F2zIh25qFIVLnrrXsrKYoCVBcWH6y6YOh1DqCzTcrRm7Nyu5TIWPM2elO3MRU6zQ0wwCpoWaHqjgyCQIY9AsVwsqsYqhQiL1%2BAHDUnnamAM4iVJ6Bwe1MJJVwV1B5KEFNpSFHuRtVcdutddZ6kNPHZBOaO4rRFvuBsNZ4V5yQZ9SVugsGrezOQJD3wZX9fEJdeM9ZI0PCtb5aNOOi%2FAayMcLaQbtL4%2Bmhx6fsvgEBbcEdyI%3D" data-url="https://login.microsoftonline.com/6e06e42d-6925-47c6-b9e7-9581c7ca302a/saml2?RelayState=ViLHS0p0OiJG5l900tbeK4tycY_Lj_BICog5X6Wuxz2CxJXwWIl5WPpssrIvJdWRq4SKhjDUnl1jQ6lie8EgTDAUnmpuW4eJ3_3NwDET8hg&amp;SAMLRequest=jZLNbtswEITveQqBd0kU9WOLsBwoMYoaSGMhdnvIpaColU2AIl2Scts8fWnFQYMWCXJdzizn293F9a9BBicwVmhVoSTC6Hp5tbBskEdaj%2B6gHuDHCNYFXqcsnR4qNBpFNbPCUsUGsNRxuq2%2F3FESYXo02mmuJXpled%2FBrAXjfAAUrFcV%2Bo4Jm7dFmvcdn5VslneQcZaVPMN9j%2BdpQnCR4rwrABdthktS5pD3PZuTpMsInhPfxtoR1so6plyFCCZ5mJCQpDucU1zQhDyi4NsLtI%2BAgpVnFIq5qXJw7mhpHEu9FyoaBDfa6t5pJYWCiOshPv8NGenCovS9sxkvwraEWVjm84TPOEs9Q3wmn8I0nlCcoEI9kxZQ0FxGdCNUJ9T%2B%2Fem0zyJLP%2B92TdhstjsU1C8Tu9XKjgOYLZiT4PD14e5v%2Br1wh7GNOjiB1EcwEZNSMPUUCT1Fi%2FmzGS2nfdNpaGb5Afsifm24XMu9T75eNVoK%2FjuopdQ%2Fbw0w56mdGT30J20G5t5mTaJkqogu7CcpHZU9Ahe9gA7Fl5AeuBNnchvca3cDXgpvbdgLNmpj6t6B%2BVeTJJPGt43%2FP%2Fbl1R8%3D&amp;SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&amp;Signature=EHlRmWGXO32GF4cmrBYhTDQvTCeZEfos5xXzHZC4d1xt2EELUWiqt4vgGbrEhIp%2B8%2BAsWqRDowMgo1fiuHMRabweemK5trOE7nnYBYAlqyRihrMbDfFKnPzi1unDUvrRJbBS2s8R9maM%2FfIatsFcAitlVsm3HfPYiD%2BOVHX%2Ftbcw1BlzverQOLfP%2FOS40Ytb6rM6YqAq2bM5aGRN5UU0MrF%2F8gstWw8B%2BNfmuiQzxIkstDCnAKhA0RO2FTQgs6m3dkeoDZyKX3bNpAKrh%2Bc6TQ2FK%2FZWf1ftXtTmeW0o66cX6zYtnHg5NNck618sZoXYRsN3WmwuiuYGN4nllRZ9%2BZMXGy3DnvHwXX46ojAODprW1mIeJFt8BJ18MCduvUsU9BPwof7%2BLlR%2Bi5oKsXfXzdEkrMDwy4NdrbJnvV22SjCJtVxfSWyZ6thtwXWd%2F2zIh25qFIVLnrrXsrKYoCVBcWH6y6YOh1DqCzTcrRm7Nyu5TIWPM2elO3MRU6zQ0wwCpoWaHqjgyCQIY9AsVwsqsYqhQiL1%2BAHDUnnamAM4iVJ6Bwe1MJJVwV1B5KEFNpSFHuRtVcdutddZ6kNPHZBOaO4rRFvuBsNZ4V5yQZ9SVugsGrezOQJD3wZX9fEJdeM9ZI0PCtb5aNOOi%2FAayMcLaQbtL4%2Bmhx6fsvgEBbcEdyI%3D">
  <meta name="viewport" content="width=device-width">
  <link crossorigin="use-credentials" media="all" rel="stylesheet" href="https://github.developer.allianz.io/assets/light-f552bab6ce72.css" /><link crossorigin="use-credentials" media="all" rel="stylesheet" href="https://github.developer.allianz.io/assets/dark-4589f64a2275.css" /><link data-color-theme="dark_dimmed" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/dark_dimmed-a7246d2d6733.css" /><link data-color-theme="dark_high_contrast" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/dark_high_contrast-f2ef05cef2f1.css" /><link data-color-theme="dark_colorblind" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/dark_colorblind-daa1fe317131.css" /><link data-color-theme="light_colorblind" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/light_colorblind-1ab6fcc64845.css" /><link data-color-theme="light_high_contrast" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/light_high_contrast-46de871e876c.css" /><link data-color-theme="light_tritanopia" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/light_tritanopia-c9754fef2a31.css" /><link data-color-theme="dark_tritanopia" crossorigin="use-credentials" media="all" rel="stylesheet" data-href="https://github.developer.allianz.io/assets/dark_tritanopia-dba748981a29.css" />
  <link crossorigin="use-credentials" media="all" rel="stylesheet" href="https://github.developer.allianz.io/assets/primer-87f353b17355.css" />
  <link crossorigin="use-credentials" media="all" rel="stylesheet" href="https://github.developer.allianz.io/assets/global-3bc9106fb3ff.css" />



  <link rel="mask-icon" href="https://github.developer.allianz.io/assets/pinned-octocat-093da3e6fa40.svg" color="#000000">
  <link rel="alternate icon" class="js-site-favicon" type="image/png" href="https://github.developer.allianz.io/favicons/favicon-ent.png">
  <link rel="icon" class="js-site-favicon" type="image/svg+xml" href="https://github.developer.allianz.io/favicons/favicon-ent.svg">

<meta name="theme-color" content="#1e2327">
<meta name="color-scheme" content="light dark" />

  <meta name="msapplication-TileImage" content="/windows-tile.png">
  <meta name="msapplication-TileColor" content="#ffffff">

  <link rel="manifest" href="/manifest.json" crossOrigin="use-credentials">

  </head>

  <body  style="word-wrap: break-word;">
    <div data-turbo-body  style="word-wrap: break-word;">
      
  
<div class="container-md px-3">
  <div data-view-component="true" class="blankslate mt-5">
    <svg aria-hidden="true" height="24" viewBox="0 0 24 24" version="1.1" width="24" data-view-component="true" class="octicon octicon-shield-lock blankslate-icon">
    <path d="M11.46 1.137a1.748 1.748 0 0 1 1.08 0l8.25 2.675A1.75 1.75 0 0 1 22 5.476V10.5c0 6.19-3.77 10.705-9.401 12.83a1.704 1.704 0 0 1-1.198 0C5.771 21.204 2 16.69 2 10.5V5.476c0-.76.49-1.43 1.21-1.664Zm.617 1.426a.253.253 0 0 0-.154 0L3.673 5.24a.25.25 0 0 0-.173.237V10.5c0 5.461 3.28 9.483 8.43 11.426a.199.199 0 0 0 .14 0c5.15-1.943 8.43-5.965 8.43-11.426V5.476a.25.25 0 0 0-.173-.237ZM13 12.232V15a1 1 0 0 1-2 0v-2.768a2 2 0 1 1 2 0Z"></path>
</svg>
    <h3 data-view-component="true" class="mb-1">You are being redirected to your identity provider in order to authenticate.</h3>
  
    <p>
      If your browser does not redirect you back, please <a id="redirect" aria-label="click here to redirect you back" class="Link--inTextBlock" href="https://login.microsoftonline.com/6e06e42d-6925-47c6-b9e7-9581c7ca302a/saml2?RelayState=ViLHS0p0OiJG5l900tbeK4tycY_Lj_BICog5X6Wuxz2CxJXwWIl5WPpssrIvJdWRq4SKhjDUnl1jQ6lie8EgTDAUnmpuW4eJ3_3NwDET8hg&amp;SAMLRequest=jZLNbtswEITveQqBd0kU9WOLsBwoMYoaSGMhdnvIpaColU2AIl2Scts8fWnFQYMWCXJdzizn293F9a9BBicwVmhVoSTC6Hp5tbBskEdaj%2B6gHuDHCNYFXqcsnR4qNBpFNbPCUsUGsNRxuq2%2F3FESYXo02mmuJXpled%2FBrAXjfAAUrFcV%2Bo4Jm7dFmvcdn5VslneQcZaVPMN9j%2BdpQnCR4rwrABdthktS5pD3PZuTpMsInhPfxtoR1so6plyFCCZ5mJCQpDucU1zQhDyi4NsLtI%2BAgpVnFIq5qXJw7mhpHEu9FyoaBDfa6t5pJYWCiOshPv8NGenCovS9sxkvwraEWVjm84TPOEs9Q3wmn8I0nlCcoEI9kxZQ0FxGdCNUJ9T%2B%2Fem0zyJLP%2B92TdhstjsU1C8Tu9XKjgOYLZiT4PD14e5v%2Br1wh7GNOjiB1EcwEZNSMPUUCT1Fi%2FmzGS2nfdNpaGb5Afsifm24XMu9T75eNVoK%2FjuopdQ%2Fbw0w56mdGT30J20G5t5mTaJkqogu7CcpHZU9Ahe9gA7Fl5AeuBNnchvca3cDXgpvbdgLNmpj6t6B%2BVeTJJPGt43%2FP%2Fbl1R8%3D&amp;SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&amp;Signature=EHlRmWGXO32GF4cmrBYhTDQvTCeZEfos5xXzHZC4d1xt2EELUWiqt4vgGbrEhIp%2B8%2BAsWqRDowMgo1fiuHMRabweemK5trOE7nnYBYAlqyRihrMbDfFKnPzi1unDUvrRJbBS2s8R9maM%2FfIatsFcAitlVsm3HfPYiD%2BOVHX%2Ftbcw1BlzverQOLfP%2FOS40Ytb6rM6YqAq2bM5aGRN5UU0MrF%2F8gstWw8B%2BNfmuiQzxIkstDCnAKhA0RO2FTQgs6m3dkeoDZyKX3bNpAKrh%2Bc6TQ2FK%2FZWf1ftXtTmeW0o66cX6zYtnHg5NNck618sZoXYRsN3WmwuiuYGN4nllRZ9%2BZMXGy3DnvHwXX46ojAODprW1mIeJFt8BJ18MCduvUsU9BPwof7%2BLlR%2Bi5oKsXfXzdEkrMDwy4NdrbJnvV22SjCJtVxfSWyZ6thtwXWd%2F2zIh25qFIVLnrrXsrKYoCVBcWH6y6YOh1DqCzTcrRm7Nyu5TIWPM2elO3MRU6zQ0wwCpoWaHqjgyCQIY9AsVwsqsYqhQiL1%2BAHDUnnamAM4iVJ6Bwe1MJJVwV1B5KEFNpSFHuRtVcdutddZ6kNPHZBOaO4rRFvuBsNZ4V5yQZ9SVugsGrezOQJD3wZX9fEJdeM9ZI0PCtb5aNOOi%2FAayMcLaQbtL4%2Bmhx6fsvgEBbcEdyI%3D">click here</a> to continue.
    </p>

</div></div>


    </div>

    <div id="js-global-screen-reader-notice" class="sr-only" aria-live="polite" aria-atomic="true" ></div>
    <div id="js-global-screen-reader-notice-assertive" class="sr-only" aria-live="assertive" aria-atomic="true"></div>
  </body>
</html>
