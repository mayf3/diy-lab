import React from 'react';
import {Composition} from 'remotion';
import catalog from '../props/catalog.json';
import {TutorialVideo, Tutorial} from './Tutorial';

type CatalogItem={id:string;props:Tutorial};
const videos=catalog as CatalogItem[];

export const Root:React.FC=()=> <>
{videos.map(({id,props})=><Composition
 key={id} id={id} component={TutorialVideo}
 durationInFrames={props.scenes.reduce((n,s)=>n+Math.round(s.seconds*props.fps),0)}
 width={props.width} height={props.height} fps={props.fps}
 defaultProps={{tutorial:props}}
/>)}
</>;
