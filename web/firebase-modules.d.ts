// The checked-in dependency tree may omit Firebase's generated barrel typings.
// Keep a small typed surface for the Firebase APIs this app actually uses.
declare module "firebase/app" {
  export interface FirebaseApp { name: string; }
  export function getApp(): FirebaseApp;
  export function getApps(): FirebaseApp[];
  export function initializeApp(options: Record<string, string | undefined>): FirebaseApp;
}

declare module "firebase/auth" {
  import type { FirebaseApp } from "firebase/app";

  export interface User {
    displayName: string | null;
    email: string | null;
    getIdToken(forceRefresh?: boolean): Promise<string>;
  }
  export interface Auth { currentUser: User | null; }
  export interface UserCredential { user: User; }
  export type Unsubscribe = () => void;
  export class GoogleAuthProvider {
    setCustomParameters(parameters: Record<string, string>): void;
  }
  export function getAuth(app: FirebaseApp): Auth;
  export function onAuthStateChanged(auth: Auth, callback: (user: User | null) => void): Unsubscribe;
  export function createUserWithEmailAndPassword(auth: Auth, email: string, password: string): Promise<UserCredential>;
  export function signInWithEmailAndPassword(auth: Auth, email: string, password: string): Promise<UserCredential>;
  export function signInWithPopup(auth: Auth, provider: GoogleAuthProvider): Promise<UserCredential>;
  export function updateProfile(user: User, profile: { displayName?: string | null }): Promise<void>;
  export function signOut(auth: Auth): Promise<void>;
}
