# Nautobot Security Notices

As a part of the Nautobot development team's commitment to security, we maintain the below historical list of security issues which have been fixed and disclosed. Note that this list **only** includes issues in Nautobot itself; while we frequently update our library dependencies to keep them up-to-date and free of known security issues therein, any reported issues in such libraries, and the corresponding updates to Nautobot's specified dependencies, are out of scope for this document.

## GHSA-wjw6-95h5-4jpx

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>June 9, 2025</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Due to insufficient security configuration of the Jinja2 templating feature used in computed fields, custom links, etc. in Nautobot:
      <ol>
        <li>A malicious user could configure this feature set in ways that could expose the value of Secrets defined in Nautobot when the templated content is rendered.</li>
        <li>A malicious user could configure this feature set in ways that could call Python APIs to modify data within Nautobot when the templated content is rendered, bypassing the object permissions assigned to the viewing user.</li>
      </ol>
    </td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-wjw6-95h5-4jpx">GHSA-wjw6-95h5-4jpx</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.32</li>
        <li>&ge;2.0.0, &lt;2.4.10</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.32 (<a href="https://github.com/nautobot/nautobot/commit/1c59263fa0284b7ad5293292c60ed03725a4603f">patch</a>)</li>
        <li>2.4.10 (<a href="https://github.com/nautobot/nautobot/commit/a8356bc06642de9c7e6b71a8c89bea6f8a86702b">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## GHSA-rh67-4c8j-hjjh

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>June 9, 2025</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Files uploaded by users to Nautobot's <code>MEDIA_ROOT</code> directory, including DeviceType image attachments as well as images attached to a Location, Device, or Rack, are served to users via a URL endpoint that was not enforcing user authentication. As a consequence, such files can be retrieved by anonymous users who know or can guess the correct URL for a given file.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-rh67-4c8j-hjjh">GHSA-rh67-4c8j-hjjh</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.32</li>
        <li>&ge;2.0.0, &lt;2.4.10</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.32 (<a href="https://github.com/nautobot/nautobot/commit/d99a53b065129cff3a0fa9abe7355a9ef1ad4c95">patch</a>)</li>
        <li>2.4.10 (<a href="https://github.com/nautobot/nautobot/commit/9c892dc300429948a4714f743c9c2879d8987340">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2024-36112

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>May 28, 2024</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>A user with permissions to view Dynamic Group records can use the Dynamic Group detail UI view and/or the Dynamic Group Members REST API view to list the objects that are members of a given Dynamic Group. Nautobot failed to restrict these listings based on the member object permissions - for example a Dynamic Group of Device objects would list all Devices that it contains, regardless of the user's <code>dcim.view_device</code> permissions or lack thereof.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-qmjf-wc2h-6x3q">GHSA-qmjf-wc2h-6x3q</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&ge;1.3.0, &lt;1.6.23</li>
        <li>&ge;2.0.0, &lt;2.2.5</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.23 (<a href="https://github.com/nautobot/nautobot/commit/3a63aa1327f943b2ac8452757ea2e4d403387ad6">patch</a>)</li>
        <li>2.2.5 (<a href="https://github.com/nautobot/nautobot/commit/4d1ff2abe2775b0a6fb16e6d1d503a78226a6f8e">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2024-34707

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>May 13, 2024</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>A Nautobot user with admin privileges can modify the <code>BANNER_TOP</code>, <code>BANNER_BOTTOM</code>, and/or <code>BANNER_LOGIN</code> configuration settings to inject arbitrary HTML, potentially exposing Nautobot users to security issues such as cross-site scripting (stored XSS).</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-r2hr-4v48-fjv3">GHSA-r2hr-4v48-fjv3</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.22</li>
        <li>&ge;2.0.0, &lt;2.2.4</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.22 (<a href="https://github.com/nautobot/nautobot/commit/4f0a66bd6307bfe0e0acb899233e0d4ad516f51c">patch</a>)</li>
        <li>2.2.4 (<a href="https://github.com/nautobot/nautobot/commit/f640aedc69c848d3d1be57f0300fc40033ff6423">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2024-32979

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>April 30, 2024</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Due to improper handling and escaping of user-provided query parameters, a maliciously crafted Nautobot URL could potentially be used to execute a Reflected Cross-Site Scripting (Reflected XSS) attack against users.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-jxgr-gcj5-cqqg">GHSA-jxgr-gcj5-cqqg</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&ge;1.5.0, &lt;1.6.20</li>
        <li>&ge;2.0.0, &lt;2.2.3</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.20 (<a href="https://github.com/nautobot/nautobot/commit/2ea5797ea43646d5d8b29433e4c707b5a9758146">patch</a>)</li>
        <li>2.2.3 (<a href="https://github.com/nautobot/nautobot/commit/42440ebd9b381534ad89d62420ebea00d703d64e">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2024-29199

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>March 25, 2024</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>A number of Nautobot URL endpoints were found to be improperly accessible to unauthenticated (anonymous) users and therefore could potentially disclose sensitive information.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4">GHSA-m732-wvh2-7cq4</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.16</li>
        <li>&ge;2.0.0, &lt;2.1.9</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.16 (<a href="https://github.com/nautobot/nautobot/commit/2fd95c365f8477b26e06d60b999ddd36882d5750">patch</a>)</li>
        <li>2.1.9 (<a href="https://github.com/nautobot/nautobot/commit/dd623e6c3307f48b6357fcc91925bcad5192abfb">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2024-23345

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>January 22, 2024</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Due to inadequate input sanitization, user-editable fields that support Markdown rendering of their contents could potentially be susceptible to cross-site scripting (XSS) attacks via maliciously crafted data.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-v4xv-795h-rv4h">GHSA-v4xv-795h-rv4h</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.10</li>
        <li>&ge;2.0.0, &lt;2.1.2</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.10 (<a href="https://github.com/nautobot/nautobot/commit/64312a4297b5ca49b6cdedf477e41e8e4fd61cce">patch</a>)</li>
        <li>2.1.2 (<a href="https://github.com/nautobot/nautobot/commit/17effcbe84a72150c82b138565c311bbee357e80">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2023-51649

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>December 22, 2023</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>When submitting a Job to run via a Job Button, only the model-level permission was checked (i.e., does the user have permission to run Jobs in general?). Object-level permissions (i.e., does the user have permission to run this specific Job?) were not enforced, possibly allowing a user to run JobButton Jobs that they should not be permitted to run.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-vf5m-xrhm-v999">GHSA-vf5m-xrhm-v999</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&ge;1.5.14, &lt;1.6.8</li>
        <li>&ge;2.0.0, &lt;2.1.0</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.8 (<a href="https://github.com/nautobot/nautobot/commit/d33d0c15a36948c45244e5b5e10bc79b8e62de7f">patch</a>)</li>
        <li>2.1.0 (<a href="https://github.com/nautobot/nautobot/commit/3d964f996f4926126c1d7853ca87b2ff475997a2">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2023-50263

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>December 12, 2023</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Unauthenticated (anonymous) users who know the name of a specific file uploaded as a Job input can potentially download the contents of that file from Nautobot.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-75mc-3pjc-727q">GHSA-75mc-3pjc-727q</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&ge;1.1.0, &lt;1.6.7</li>
        <li>&ge;2.0.0, &lt;2.0.6</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.7 (<a href="https://github.com/nautobot/nautobot/commit/7c4cf3137f45f1541f09f2f6a7f8850cd3a2eaee">patch</a>)</li>
        <li>2.0.6 (<a href="https://github.com/nautobot/nautobot/commit/458280c359a4833a20da294eaf4b8d55edc91cee">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2023-48705

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>November 21, 2023</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>A user with permission to create or edit custom links, job buttons, and/or computed fields could potentially inject a malicious payload, such as JavaScript code or cross-site scripting (XSS).</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-cf9f-wmhp-v4pr">GHSA-cf9f-wmhp-v4pr</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.6.6</li>
        <li>&ge;2.0.0, &lt;2.0.5</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.6.6 (<a href="https://github.com/nautobot/nautobot/commit/362850f5a94689a4c75e3188bf6de826c3b012b2">patch</a>)</li>
        <li>2.0.5 (<a href="https://github.com/nautobot/nautobot/commit/54abe23331b6c3d0d82bf1b028c679b1d200920d">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2023-46128

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>October 24, 2023</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Certain REST API endpoints, in combination with the ?depth=<N> query parameter, could expose hashed user passwords as stored in the database to any authenticated user with access to these endpoints.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-r2hw-74xv-4gqp">GHSA-r2hw-74xv-4gqp</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&ge;2.0.0, &lt;2.0.3</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>2.0.3 (<a href="https://github.com/nautobot/nautobot/commit/1ce8e5c658a075c29554d517cd453675e5d40d71">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>

## CVE-2023-25657

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th>Disclosure&nbsp;Date</th>
    <td>February 21, 2023</td>
  </tr>
  <tr>
    <th>Summary</th>
    <td>Lack of environment sandboxing in Jinja2 template rendering of user-authored data (computed fields, custom links, export templates, etc.) could potentially result in remote code execution.</td>
  </tr>
  <tr>
    <th>Full&nbsp;Description</th>
    <td><a href="https://github.com/nautobot/nautobot/security/advisories/GHSA-8mfq-f5wj-vw5m">GHSA-8mfq-f5wj-vw5m</a></td>
  </tr>
  <tr>
    <th>Affected&nbsp;Versions</th>
    <td>
      <ul>
        <li>&lt;1.5.7</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th>Patched&nbsp;Versions</th>
    <td>
      <ul>
        <li>1.5.7 (<a href="https://github.com/nautobot/nautobot/commit/14ec554890ddf9cce6be7dff173ecb0bd9f46793">patch</a>)</li>
      </ul>
    </td>
  </tr>
</table>
