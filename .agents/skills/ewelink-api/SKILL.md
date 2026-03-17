---
name: eWeLink API Integration
description: Instructions and patterns for integrating and controlling Sonoff/eWeLink devices using the API V2.
---

# eWeLink API Integration

This skill enables the agent to control Sonoff WiFi switches and other eWeLink-compatible devices using the eWeLink Open Platform API V2.

## Prerequisites

1.  **Credentials**: You need an `appid` and `app secret` from the [eWeLink Developer Platform](https://dev.ewelink.cc/).
2.  **Environment Variables**: The following must be set in your `.env` file:
    -   `EWELINK_APPID`: Your App ID.
    -   `EWELINK_APPSECRET`: Your App Secret.
    -   `EWELINK_REGION`: Your account region (`as`, `us`, `eu`, `cn`). Default is `eu`.
    -   `EWELINK_DEVICEID`: (Optional) The ID of the device you want to control by default.

## Usage

### Listing Devices
To see all connected devices and their current status:
```bash
python ewelink_tool.py list
```

### Controlling a Device
To turn a device ON or OFF:
```bash
python ewelink_tool.py on <device_id>
python ewelink_tool.py off <device_id>
```

## Implementation Details

The integration uses **HMAC-SHA256** signing for all requests as per eWeLink API V2 specifications.

- **Base URLs**:
  - Asia: `https://as-apia.coolkit.cc`
  - Americas: `https://us-apia.coolkit.cc`
  - Europe: `https://eu-apia.coolkit.cc`
  - China: `https://cn-apia.coolkit.cn`

- **Authentication Strategy**:
  - **Headless OAuth**: Bypass the browser-based OAuth page (which often fails with CORS errors) by directly calling `/v2/user/oauth/code` with account email and password.
  - **Region Auto-Discovery**: The API will redirect you if you hit the wrong regional shard. Always check the `region` field in response data and update the `BASE_URL` and `.env` accordingly.
  - **Token Header**: Use `Authorization: Bearer <token>` for most V2 requests, but **crucially** include `X-CK-Appid` in the same headers as some service endpoints require it even with a token.

## Troubleshooting

- **Error 407 (Path not allowed)**: Usually means the `APPID` type does not support the Direct Login endpoint. Use the **Headless OAuth** flow instead.
- **Error 406 (Permission Denied)**: The device exists but is not owned by or shared with the account. Verify the account email in the eWeLink mobile app.
- **Empty Device List**: Use `GET /v2/device/all-thing` instead of `/v2/device/thing` to find devices shared with the user.
- **Share Approval**: If a device is shared but doesn't appear, check messages via `/v2/message/read` and approve via `/v2/device/share/permit`.
- **Region Desync**: If a token is rejected with 401, it may be because you are hitting a different regional shard than where the token was issued. Reset `.env` tokens and re-login to re-sync.
- **Signature Error**: Ensure the App Secret is correct and the signing message is correctly formatted (JSON string for POST, sorted query string for GET).
- **Region Issues**: If you get a "Region error" or cannot find devices, try changing `EWELINK_REGION` in `.env`.
- **Offline Devices**: Ensure the Sonoff switch is connected to WiFi and showing as "online" in the eWeLink app.
