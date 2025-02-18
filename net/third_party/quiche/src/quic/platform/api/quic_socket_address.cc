// Copyright (c) 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <string>

#include "net/third_party/quiche/src/quic/platform/api/quic_socket_address.h"

namespace quic {

QuicSocketAddress::QuicSocketAddress(QuicIpAddress address, uint16_t port)
    : impl_(address, port) {}

QuicSocketAddress::QuicSocketAddress(const struct sockaddr_storage& saddr)
    : impl_(saddr) {}

QuicSocketAddress::QuicSocketAddress(const sockaddr* saddr, socklen_t len)
    : impl_(saddr, len) {}

QuicSocketAddress::QuicSocketAddress(const QuicSocketAddressImpl& impl)
    : impl_(impl) {}

bool operator==(const QuicSocketAddress& lhs, const QuicSocketAddress& rhs) {
  return lhs.impl_ == rhs.impl_;
}

bool operator!=(const QuicSocketAddress& lhs, const QuicSocketAddress& rhs) {
  return lhs.impl_ != rhs.impl_;
}

bool QuicSocketAddress::IsInitialized() const {
  return impl_.IsInitialized();
}

std::string QuicSocketAddress::ToString() const {
  return impl_.ToString();
}

int QuicSocketAddress::FromSocket(int fd) {
  return impl_.FromSocket(fd);
}

QuicSocketAddress QuicSocketAddress::Normalized() const {
  return QuicSocketAddress(impl_.Normalized());
}

QuicIpAddress QuicSocketAddress::host() const {
  return QuicIpAddress(impl_.host());
}

uint16_t QuicSocketAddress::port() const {
  return impl_.port();
}

sockaddr_storage QuicSocketAddress::generic_address() const {
  return impl_.generic_address();
}

}  // namespace quic
