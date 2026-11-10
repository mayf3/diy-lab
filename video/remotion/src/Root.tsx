import React from 'react';
import {Composition} from 'remotion';
import catalog from '../props/catalog.json';
import {TutorialVideo, Tutorial} from './Tutorial';
import {ChristmasHandsOn, DURATION, HANDS_ON_FPS} from './ChristmasHandsOn';

type CatalogItem={id:string;props:Tutorial};
const videos=catalog as CatalogItem[];

export const Root:React.FC=()=> <>
<Composition id="ChristmasHandsOnLesson1" component={ChristmasHandsOn} durationInFrames={DURATION} width={1280} height={720} fps={HANDS_ON_FPS} />
{videos.map(({id,props})=><Composition
 key={id} id={id} component={TutorialVideo}
 durationInFrames={props.scenes.reduce((n,s)=>n+Math.round(s.seconds*props.fps),0)}
 width={props.width} height={props.height} fps={props.fps}
 defaultProps={{tutorial:props}}
/>)}
</>;
