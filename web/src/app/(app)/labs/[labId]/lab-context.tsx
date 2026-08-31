"use client";

import { createContext, useContext } from "react";

import type { LabDetail } from "@/lib/api";

const LabContext = createContext<LabDetail | null>(null);

export const LabProvider = LabContext.Provider;

export function useLab(): LabDetail {
  const lab = useContext(LabContext);
  if (!lab) throw new Error("useLab must be used inside a lab route");
  return lab;
}
